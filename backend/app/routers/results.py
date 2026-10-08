from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import AnalysisResult, AnalysisTask, Conversation, User
from ..schemas import ResultOut
from ..services.file_service import resolve_inside
from ..services.task_service import result_to_dict


router = APIRouter(tags=["results"])


def _get_owned_result(db: Session, task_id: int, user: User) -> AnalysisResult:
    result = db.scalar(
        select(AnalysisResult)
        .join(AnalysisTask, AnalysisTask.id == AnalysisResult.task_id)
        .join(Conversation, Conversation.id == AnalysisTask.conversation_id)
        .where(AnalysisResult.task_id == task_id, Conversation.user_id == user.id)
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析结果不存在")
    return result


@router.get("/api/results/{task_id}", response_model=ResultOut)
def get_result(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return result_to_dict(_get_owned_result(db, task_id, user))


@router.get("/api/results/{task_id}/download")
def download_result(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    result = _get_owned_result(db, task_id, user)
    if not result.result_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="结果文件不存在")
    try:
        path = resolve_inside(settings.exports_dir, result.result_file_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结果文件路径非法") from exc
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="结果文件不存在")
    return FileResponse(path, filename=path.name, media_type="text/markdown; charset=utf-8")


@router.post("/api/results/{task_id}/save")
def save_result(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = _get_owned_result(db, task_id, user)
    target = settings.exports_dir / str(user.id) / str(result.conversation_id) / f"task_{task_id}_result.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.result_markdown, encoding="utf-8")
    result.result_file_path = str(target)
    db.commit()
    return {"status": "saved", "file_path": str(target), "file_name": target.name}
