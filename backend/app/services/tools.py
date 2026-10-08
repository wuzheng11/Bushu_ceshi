from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config import settings
from ..database import create_database_engine


@dataclass
class ToolExecution:
    tool_name: str
    status: str
    summary: str
    data: dict[str, Any]


class DatabaseQueryTool:
    allowed_tables = {
        "business_users",
        "category_master",
        "product_master",
        "search_impressions",
        "product_clicks",
        "product_conversions",
        "visit_events",
        "add_cart_events",
        "order_events",
    }
    forbidden = {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "attach",
        "detach",
        "pragma",
        "vacuum",
    }

    def __init__(self, max_rows: int = 500) -> None:
        self.max_rows = max_rows
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_database_engine(settings.demo_database_url)
        return self._engine

    def validate_sql(self, sql: str) -> str:
        normalized = re.sub(r"\s+", " ", sql.strip()).strip().lower()
        if not (normalized.startswith("select ") or normalized.startswith("with ")):
            raise ValueError("只允许只读 SELECT/WITH 查询")
        if ";" in normalized.rstrip(";"):
            raise ValueError("不允许执行多条 SQL")
        if any(re.search(rf"\b{word}\b", normalized) for word in self.forbidden):
            raise ValueError("查询包含禁止写入的关键字")
        tables = set(re.findall(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", normalized))
        unknown = tables - self.allowed_tables
        if unknown:
            raise ValueError(f"数据表未授权: {', '.join(sorted(unknown))}")
        return sql

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> ToolExecution:
        safe_sql = self.validate_sql(sql)
        with self.engine.connect() as connection:
            rows = connection.execute(text(safe_sql), params or {}).mappings().all()
        limited = [dict(row) for row in rows[: self.max_rows]]
        return ToolExecution(
            tool_name="database_query",
            status="success",
            summary=f"查询返回 {len(limited)} 行，最多允许 {self.max_rows} 行",
            data={"rows": limited, "row_count": len(limited)},
        )


class ConversationFileTool:
    def __init__(self, user_id: int, conversation_id: int) -> None:
        self.root = (
            settings.workspace_dir / str(user_id) / str(conversation_id)
        ).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe(self, relative_path: str) -> Path:
        target = (self.root / relative_path).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError("文件路径越界")
        return target

    def write_text(self, relative_path: str, content: str) -> ToolExecution:
        target = self._safe(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolExecution(
            tool_name="file_write",
            status="success",
            summary=f"写入文件 {target.name}，{len(content.encode('utf-8'))} 字节",
            data={"file_path": str(target)},
        )

    def write_json(self, relative_path: str, payload: Any) -> ToolExecution:
        return self.write_text(
            relative_path,
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        )

    def read_text(self, relative_path: str, max_chars: int = 100_000) -> ToolExecution:
        target = self._safe(relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(str(target))
        content = target.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        return ToolExecution(
            tool_name="file_read",
            status="success",
            summary=f"读取文件 {target.name}，{len(content)} 字符",
            data={"content": content, "file_path": str(target)},
        )


class TextSearchTool:
    built_in_documents = {
        "商品目录运营手册.md": (
            "高曝光低点击通常优先排查标题、主图、价格带、类目错放与属性完整度。"
            "商品目录优化应先修复高流量类目的入口质量问题，再验证点击率与转化率。"
        ),
        "客户转化漏斗手册.md": (
            "访问到加购反映商品兴趣与详情页说服力，加购到下单反映价格、运费、库存、"
            "支付流程和优惠策略。应按渠道、城市、用户分群拆解流失。"
        ),
        "经营归因方法.md": (
            "归因分析应区分相关性与因果性，至少给出指标变化、证据、影响范围、缺失数据和下一步验证动作。"
        ),
    }

    def __init__(self, user_id: int, conversation_id: int) -> None:
        self.upload_root = settings.uploads_dir / str(user_id) / str(conversation_id)

    @staticmethod
    def _tokens(text_value: str) -> set[str]:
        chinese = set(re.findall(r"[\u4e00-\u9fff]{2,}", text_value))
        words = set(re.findall(r"[a-zA-Z0-9_]{2,}", text_value.lower()))
        return chinese | words

    def search(self, query: str, attachment_paths: list[Path] | None = None, limit: int = 8) -> ToolExecution:
        query_tokens = self._tokens(query)
        candidates: list[tuple[str, str, str]] = [
            ("built_in", name, body) for name, body in self.built_in_documents.items()
        ]
        paths = list(attachment_paths or [])
        if self.upload_root.exists():
            known = {str(path.resolve()) for path in paths}
            paths.extend(
                path for path in self.upload_root.rglob("*")
                if path.is_file() and str(path.resolve()) not in known
            )
        for path in paths:
            if path.suffix.lower() not in {".txt", ".md", ".csv", ".json", ".log", ".sql"}:
                continue
            try:
                body = path.read_text(encoding="utf-8", errors="ignore")[:200_000]
            except OSError:
                continue
            candidates.append(("attachment", path.name, body))

        scored: list[dict[str, Any]] = []
        for source_type, name, body in candidates:
            body_tokens = self._tokens(body)
            score = len(query_tokens & body_tokens)
            if score or source_type == "built_in":
                excerpt = body[:260].replace("\n", " ")
                scored.append(
                    {
                        "source_type": source_type,
                        "source_name": name,
                        "score": score,
                        "excerpt": excerpt,
                    }
                )
        scored.sort(key=lambda item: (item["score"], item["source_type"] == "built_in"), reverse=True)
        results = scored[:limit]
        return ToolExecution(
            tool_name="text_search",
            status="success",
            summary=f"检索 {len(candidates)} 个文本来源，命中 {len(results)} 条",
            data={"matches": results},
        )


class SafeCommandTool:
    ALLOWED_COMMANDS = {
        "python_version": [sys.executable, "--version"],
        "worker_check": [sys.executable, "-c", "print('analysis-worker-ok')"],
    }

    def run(self, command_key: str) -> ToolExecution:
        if command_key not in self.ALLOWED_COMMANDS:
            raise ValueError("命令不在安全白名单中")
        completed = subprocess.run(
            self.ALLOWED_COMMANDS[command_key],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )
        output = (completed.stdout or completed.stderr).strip()
        return ToolExecution(
            tool_name="command_execution",
            status="success" if completed.returncode == 0 else "failed",
            summary=f"{command_key}: {output[:300]}",
            data={"return_code": completed.returncode, "output": output},
        )


class RuleBasedLLMProvider:
    """可替换的 LLM 占位实现。

    如果接入真实模型，只需保持 generate_report 的输入输出结构不变。
    """

    def generate_report(self, context: dict[str, Any]) -> dict[str, Any]:
        return context
