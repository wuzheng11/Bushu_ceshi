from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import settings


def safe_filename(name: str) -> str:
    clean = Path(name).name
    clean = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", clean).strip("._")
    return clean or "file"


def conversation_directory(root: Path, user_id: int, conversation_id: int) -> Path:
    path = (root / str(user_id) / str(conversation_id)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise ValueError("非法文件目录")
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_inside(root: Path, candidate: str | Path) -> Path:
    root_resolved = root.resolve()
    target = Path(candidate).resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError("文件路径越界")
    return target


def delete_conversation_files(user_id: int, conversation_id: int) -> None:
    for root in (settings.uploads_dir, settings.exports_dir, settings.workspace_dir):
        path = root / str(user_id) / str(conversation_id)
        if path.exists():
            for child in sorted(path.rglob("*"), reverse=True):
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    child.rmdir()
            path.rmdir()


def write_json_file(path: Path, payload: dict[str, Any] | list[Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path
