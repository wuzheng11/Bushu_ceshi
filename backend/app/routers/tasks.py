from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AnalysisTask, Conversation, TaskLog, User
from ..schemas import TaskOut


router = APIRouter(tags=["tasks"])


def _get_owned_task(db: Session, task_id: int, user: User) -> AnalysisTask:
    task = db.scalar(
        select(AnalysisTask)
        .join(Conversation, Conversation.id == AnalysisTask.conversation_id)
        .where(AnalysisTask.id == task_id, Conversation.user_id == user.id)
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


def _task_dict(task: AnalysisTask) -> dict:
    return {
        "task_id": task.id,
        "conversation_id": task.conversation_id,
        "task_status": task.task_status,
        "current_step": task.current_step,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "error_message": task.error_message,
    }


@router.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return _task_dict(_get_owned_task(db, task_id, user))


@router.get("/api/tasks")
def list_tasks(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    tasks = db.scalars(
        select(AnalysisTask)
        .join(Conversation, Conversation.id == AnalysisTask.conversation_id)
        .where(
            AnalysisTask.conversation_id == conversation_id,
            Conversation.user_id == user.id,
        )
        .order_by(AnalysisTask.id.desc())
    ).all()
    return [_task_dict(item) for item in tasks]


@router.post("/api/tasks/{task_id}/cancel")
def cancel_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = _get_owned_task(db, task_id, user)
    if task.task_status in {"queued", "running"}:
        task.task_status = "cancelled"
        task.current_step = "任务已取消"
        task.finished_at = datetime.now(timezone.utc)
        db.commit()
    return _task_dict(task)


@router.get("/api/tasks/{task_id}/events")
def list_task_events(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    _get_owned_task(db, task_id, user)
    logs = db.scalars(
        select(TaskLog).where(TaskLog.task_id == task_id).order_by(TaskLog.created_at.asc())
    ).all()
    return [
        {
            "id": item.id,
            "log_level": item.log_level,
            "log_type": item.log_type,
            "log_content": item.log_content,
            "created_at": item.created_at,
        }
        for item in logs
    ]
