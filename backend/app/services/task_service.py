from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from ..config import settings
from ..database import SessionLocal
from ..models import (
    AnalysisResult,
    AnalysisTask,
    Attachment,
    ContextSummary,
    Conversation,
    Message,
    TaskLog,
)
from .analysis_engine import AnalysisContext, AnalysisEngine, AnalysisOutcome
from .config_service import config_service
from .websocket_manager import websocket_manager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def result_to_dict(result: AnalysisResult) -> dict[str, Any]:
    return {
        "result_id": result.id,
        "task_id": result.task_id,
        "problem_definition": result.problem_definition,
        "key_metrics": json.loads(result.key_metrics_json),
        "evidence_list": json.loads(result.evidence_list_json),
        "conclusion_text": result.conclusion_text,
        "missing_data_text": result.missing_data_text,
        "next_action_text": result.next_action_text,
        "result_markdown": result.result_markdown,
        "result_file_path": result.result_file_path,
        "created_at": result.created_at,
    }


async def publish_event(
    task_id: int,
    conversation_id: int,
    event_type: str,
    payload: dict[str, Any],
    log_level: str = "INFO",
) -> None:
    event_payload = {
        "event": event_type,
        "task_id": task_id,
        "conversation_id": conversation_id,
        "timestamp": utcnow().isoformat(),
        **payload,
    }
    with SessionLocal() as db:
        task = db.get(AnalysisTask, task_id)
        if not task:
            return
        db.add(
            TaskLog(
                task_id=task_id,
                log_level=log_level,
                log_type=event_type,
                log_content=json.dumps(event_payload, ensure_ascii=False, default=str),
            )
        )
        db.commit()
    await websocket_manager.broadcast(conversation_id, event_payload)


class TaskService:
    def __init__(self) -> None:
        self.engine = AnalysisEngine()

    async def run(self, task_id: int) -> None:
        db = SessionLocal()
        try:
            task = db.get(AnalysisTask, task_id)
            if not task or task.task_status in {"cancelled", "success", "failed"}:
                return

            task.task_status = "running"
            task.current_step = "准备分析上下文"
            task.started_at = utcnow()
            next_seq = (
                db.scalar(
                    select(func.max(Message.seq_no)).where(
                        Message.conversation_id == task.conversation_id
                    )
                )
                or 0
            ) + 1
            assistant_message = Message(
                conversation_id=task.conversation_id,
                role="assistant",
                message_type="analysis",
                content="",
                seq_no=next_seq,
            )
            db.add(assistant_message)
            conversation = db.get(Conversation, task.conversation_id)
            if conversation:
                conversation.last_message_at = utcnow()
                conversation.updated_at = utcnow()
            db.commit()
            db.refresh(assistant_message)

            await publish_event(
                task.id,
                task.conversation_id,
                "message_start",
                {"message_id": assistant_message.id, "role": "assistant"},
            )

            attachments = db.scalars(
                select(Attachment).where(
                    Attachment.conversation_id == task.conversation_id,
                    Attachment.id.in_(
                        [
                            int(item)
                            for item in task.input_text.split("::attachments::")[-1].split(",")
                            if item.strip().isdigit()
                        ]
                    )
                    if "::attachments::" in task.input_text
                    else Attachment.id < 0,
                )
            ).all()
            attachment_paths = [Path(item.file_path) for item in attachments]
            previous_summary = db.scalar(
                select(ContextSummary.summary_text)
                .where(ContextSummary.conversation_id == task.conversation_id)
                .order_by(ContextSummary.created_at.desc())
                .limit(1)
            )
            config = {
                "default_scenario": config_service.get("analysis.default_scenario", "auto"),
                "max_database_rows": config_service.get_int("analysis.max_database_rows", 500),
                "min_impressions": config_service.get_int("analysis.min_impressions", 1000),
                "low_ctr_threshold": config_service.get_float("analysis.low_ctr_threshold", 0.035),
                "low_cvr_threshold": config_service.get_float("analysis.low_cvr_threshold", 0.025),
                "enable_command_tool": config_service.get_bool(
                    "analysis.enable_command_tool",
                    config_service.get_bool("feature.command_tool", True),
                ),
                "enable_text_search": config_service.get_bool("analysis.enable_text_search", True),
                "enable_llm_placeholder": config_service.get_bool(
                    "analysis.enable_llm_placeholder", True
                ),
            }
            analysis_input = task.input_text.split("::attachments::", 1)[0]
            context = AnalysisContext(
                task_id=task.id,
                conversation_id=task.conversation_id,
                user_id=task.user_id,
                input_text=analysis_input,
                attachment_paths=attachment_paths,
                previous_summary=previous_summary,
                config=config,
            )

            async def engine_publish(event_type: str, payload: dict[str, Any]) -> None:
                fresh = db.get(AnalysisTask, task.id)
                if fresh and fresh.task_status == "cancelled":
                    raise asyncio.CancelledError("任务已取消")
                if event_type == "task_status":
                    fresh = db.get(AnalysisTask, task.id)
                    if fresh:
                        fresh.task_status = payload.get("task_status", fresh.task_status)
                        fresh.current_step = payload.get("current_step", fresh.current_step)
                        db.commit()
                await publish_event(task.id, task.conversation_id, event_type, payload)

            outcome = await self.engine.run(context, engine_publish)
            if db.get(AnalysisTask, task.id).task_status == "cancelled":
                return

            markdown = self._build_markdown(task, outcome)
            export_path = self._write_export(task.user_id, task.conversation_id, task.id, markdown)
            await publish_event(
                task.id,
                task.conversation_id,
                "tool_start",
                {"tool_name": "result_export"},
            )
            await publish_event(
                task.id,
                task.conversation_id,
                "tool_finish",
                {
                    "tool_name": "result_export",
                    "tool_status": "success",
                    "tool_result_summary": f"结果文件已生成：{export_path.name}",
                },
            )

            result = AnalysisResult(
                task_id=task.id,
                conversation_id=task.conversation_id,
                problem_definition=outcome.problem_definition,
                key_metrics_json=json.dumps(outcome.key_metrics, ensure_ascii=False),
                evidence_list_json=json.dumps(outcome.evidence_list, ensure_ascii=False),
                conclusion_text=outcome.conclusion_text,
                missing_data_text=outcome.missing_data_text,
                next_action_text=outcome.next_action_text,
                result_markdown=markdown,
                result_file_path=str(export_path),
            )
            db.add(result)
            assistant_message.content = markdown
            assistant_message.message_type = "result"
            task.task_status = "success"
            task.current_step = "分析完成"
            task.finished_at = utcnow()
            task.error_message = None
            conversation = db.get(Conversation, task.conversation_id)
            if conversation:
                conversation.last_message_at = task.finished_at
                conversation.updated_at = task.finished_at
            db.flush()
            db.add(
                ContextSummary(
                    conversation_id=task.conversation_id,
                    start_seq_no=assistant_message.seq_no - 1,
                    end_seq_no=assistant_message.seq_no,
                    summary_text=(
                        f"问题：{analysis_input[:160]}；"
                        f"场景：{outcome.scenario}；结论：{outcome.conclusion_text[:240]}"
                    ),
                )
            )
            db.commit()
            db.refresh(result)

            for chunk in self._chunk_text(markdown, 900):
                await publish_event(
                    task.id,
                    task.conversation_id,
                    "message_delta",
                    {"delta_text": chunk, "message_id": assistant_message.id},
                )
            await publish_event(
                task.id,
                task.conversation_id,
                "result_ready",
                {"result_id": result.id},
            )
            await publish_event(
                task.id,
                task.conversation_id,
                "task_status",
                {"task_status": "success", "current_step": "分析完成"},
            )
            await publish_event(
                task.id,
                task.conversation_id,
                "done",
                {"finished_at": _as_iso(task.finished_at)},
            )
        except asyncio.CancelledError:
            db.rollback()
            task = db.get(AnalysisTask, task_id)
            if task and task.task_status != "success":
                task.task_status = "cancelled"
                task.current_step = "任务已取消"
                task.finished_at = utcnow()
                db.commit()
                await publish_event(
                    task.id,
                    task.conversation_id,
                    "task_status",
                    {"task_status": "cancelled", "current_step": "任务已取消"},
                )
        except Exception as exc:
            db.rollback()
            task = db.get(AnalysisTask, task_id)
            if not task:
                return
            task.task_status = "failed"
            task.current_step = "分析失败"
            task.error_message = str(exc)
            task.finished_at = utcnow()
            db.commit()
            await publish_event(
                task.id,
                task.conversation_id,
                "error",
                {"error_message": str(exc)},
                log_level="ERROR",
            )
            await publish_event(
                task.id,
                task.conversation_id,
                "task_status",
                {"task_status": "failed", "current_step": "分析失败"},
                log_level="ERROR",
            )
            await publish_event(
                task.id,
                task.conversation_id,
                "done",
                {"finished_at": _as_iso(task.finished_at)},
            )
        finally:
            db.close()

    @staticmethod
    def _build_markdown(task: AnalysisTask, outcome: AnalysisOutcome) -> str:
        metric_lines = "\n".join(
            f"- **{item['metric_name']}**：{item['metric_value']} {item['metric_unit']}（{item['metric_period']}）"
            for item in outcome.key_metrics
        )
        evidence_lines = "\n".join(
            f"- [{item['source_type']}] {item['source_name']}：{item['evidence_text']} "
            f"（置信度 {float(item['confidence']):.2f}）"
            for item in outcome.evidence_list
        )
        return (
            f"# 经营归因分析报告\n\n"
            f"- 任务编号：{task.id}\n"
            f"- 场景：{outcome.scenario}\n"
            f"- 用户问题：{task.input_text.split('::attachments::', 1)[0]}\n\n"
            f"## 1. 问题定义\n\n{outcome.problem_definition}\n\n"
            f"## 2. 关键指标\n\n{metric_lines}\n\n"
            f"## 3. 证据列表\n\n{evidence_lines}\n\n"
            f"## 4. 归因结论\n\n{outcome.conclusion_text}\n\n"
            f"## 5. 待补充数据\n\n{outcome.missing_data_text}\n\n"
            f"## 6. 下一步建议\n\n{outcome.next_action_text}\n"
        )

    @staticmethod
    def _write_export(user_id: int, conversation_id: int, task_id: int, markdown: str) -> Path:
        export_dir = settings.exports_dir / str(user_id) / str(conversation_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        path = export_dir / f"task_{task_id}_result.md"
        path.write_text(markdown, encoding="utf-8")
        return path

    @staticmethod
    def _chunk_text(content: str, size: int) -> list[str]:
        return [content[index : index + size] for index in range(0, len(content), size)]


task_service = TaskService()
