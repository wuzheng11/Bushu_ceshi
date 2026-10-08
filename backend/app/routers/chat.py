from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, get_db
from ..deps import get_current_user, get_owned_conversation_or_404
from ..models import (
    AnalysisTask,
    Attachment,
    Conversation,
    Message,
    TaskLog,
    User,
    WebSocketToken,
)
from ..schemas import (
    ChatSend,
    ConversationCreate,
    ConversationDelete,
    ConversationOut,
    ConversationUpdate,
    WebSocketTokenOut,
)
from ..services.config_service import config_service
from ..services.task_service import task_service
from ..services.websocket_manager import websocket_manager


router = APIRouter(tags=["chat"])


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


@router.post("/api/chat/create", response_model=ConversationOut)
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    conversation = Conversation(user_id=user.id, title=payload.title, status="active")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {
        "conversation_id": conversation.id,
        "title": conversation.title,
        "status": conversation.status,
        "last_message_at": conversation.last_message_at,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


@router.post("/api/chat/delete")
def delete_conversations(
    payload: ConversationDelete,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.id.in_(payload.conversation_ids),
            Conversation.user_id == user.id,
            Conversation.status != "deleted",
        )
    ).all()
    for conversation in conversations:
        from ..models import AnalysisResult, ContextSummary

        task_ids = list(
            db.scalars(
                select(AnalysisTask.id).where(AnalysisTask.conversation_id == conversation.id)
            ).all()
        )
        if task_ids:
            db.query(TaskLog).filter(TaskLog.task_id.in_(task_ids)).delete(synchronize_session=False)
        db.query(AnalysisResult).filter(
            AnalysisResult.conversation_id == conversation.id
        ).delete(synchronize_session=False)
        db.query(ContextSummary).filter(
            ContextSummary.conversation_id == conversation.id
        ).delete(synchronize_session=False)
        db.query(Attachment).filter(Attachment.conversation_id == conversation.id).delete(
            synchronize_session=False
        )
        db.query(Message).filter(Message.conversation_id == conversation.id).delete(
            synchronize_session=False
        )
        db.query(AnalysisTask).filter(AnalysisTask.conversation_id == conversation.id).delete(
            synchronize_session=False
        )
        conversation.status = "deleted"
        from ..services.file_service import delete_conversation_files

        delete_conversation_files(user.id, conversation.id)
    db.commit()
    return {"deleted_count": len(conversations), "conversation_ids": [item.id for item in conversations]}


@router.post("/api/chat/update", response_model=ConversationOut)
def update_conversation(
    payload: ConversationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    conversation = get_owned_conversation_or_404(db, payload.conversation_id, user)
    conversation.title = payload.title
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    return {
        "conversation_id": conversation.id,
        "title": conversation.title,
        "status": conversation.status,
        "last_message_at": conversation.last_message_at,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


@router.get("/api/chat/ls", response_model=list[ConversationOut])
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.status != "deleted")
        .order_by(Conversation.updated_at.desc())
    ).all()
    return [
        {
            "conversation_id": item.id,
            "title": item.title,
            "status": item.status,
            "last_message_at": item.last_message_at,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in conversations
    ]


@router.get("/api/chat/ls/{conversation_id}")
def list_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_owned_conversation_or_404(db, conversation_id, user)
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.seq_no.asc())
    ).all()
    result: list[dict[str, Any]] = []
    for message in messages:
        attachments = db.scalars(
            select(Attachment).where(Attachment.message_id == message.id)
        ).all()
        result.append(
            {
                "message_id": message.id,
                "role": message.role,
                "message_type": message.message_type,
                "content": message.content,
                "tool_name": message.tool_name,
                "tool_status": message.tool_status,
                "seq_no": message.seq_no,
                "attachments": [
                    {
                        "attachment_id": attachment.id,
                        "file_name": attachment.file_name,
                        "file_type": attachment.file_type,
                        "file_size": attachment.file_size,
                    }
                    for attachment in attachments
                ],
                "created_at": message.created_at,
            }
        )
    return result


@router.post("/api/chat/send")
def send_message(
    payload: ChatSend,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    conversation = get_owned_conversation_or_404(db, payload.conversation_id, user)
    running = db.scalar(
        select(AnalysisTask).where(
            AnalysisTask.conversation_id == conversation.id,
            AnalysisTask.task_status.in_(["queued", "running"]),
        )
    )
    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"当前会话已有运行中的任务：{running.id}",
        )

    attachments: list[Attachment] = []
    if payload.attachment_ids:
        attachments = list(
            db.scalars(
                select(Attachment).where(
                    Attachment.id.in_(payload.attachment_ids),
                    Attachment.conversation_id == conversation.id,
                )
            ).all()
        )
        if len(attachments) != len(set(payload.attachment_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="附件不存在或不属于当前会话")

    next_seq = (
        db.scalar(
            select(func.max(Message.seq_no)).where(Message.conversation_id == conversation.id)
        )
        or 0
    ) + 1
    message = Message(
        conversation_id=conversation.id,
        role="user",
        message_type="text",
        content=payload.content,
        seq_no=next_seq,
    )
    db.add(message)
    db.flush()
    for attachment in attachments:
        attachment.message_id = message.id

    attachment_marker = ",".join(str(item.id) for item in attachments)
    task = AnalysisTask(
        conversation_id=conversation.id,
        user_id=user.id,
        input_text=(
            payload.content
            if not attachment_marker
            else f"{payload.content}::attachments::{attachment_marker}"
        ),
        task_status="queued",
        current_step="等待分析",
    )
    if conversation.title.startswith("新会话") and next_seq == 1:
        conversation.title = payload.content.strip()[:40]
    conversation.last_message_at = datetime.now(timezone.utc)
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()
    db.refresh(task)
    db.refresh(message)

    background_tasks.add_task(task_service.run, task.id)
    return {
        "message_id": message.id,
        "task_id": task.id,
        "conversation_id": conversation.id,
        "task_status": task.task_status,
        "current_step": task.current_step,
    }


@router.post("/api/chat/ws-token", response_model=WebSocketTokenOut)
def create_websocket_token(
    conversation_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_owned_conversation_or_404(db, conversation_id, user)
    expires_in = config_service.get_int("system.websocket_token_ttl_seconds", 120)
    token = WebSocketToken(
        user_id=user.id,
        conversation_id=conversation_id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    )
    db.add(token)
    db.commit()
    return {"websocket_token": token.token, "expires_in": expires_in}


@router.websocket("/api/chat/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    websocket_token: str = Query(...),
    conversation_id: int = Query(...),
) -> None:
    with SessionLocal() as db:
        token = db.scalar(
            select(WebSocketToken).where(
                WebSocketToken.token == websocket_token,
                WebSocketToken.conversation_id == conversation_id,
            )
        )
        now = datetime.now(timezone.utc)
        if (
            not token
            or token.consumed_at is not None
            or _aware(token.expires_at) < now
            or token.user_id
            != db.scalar(
                select(Conversation.user_id).where(
                    Conversation.id == conversation_id,
                    Conversation.status != "deleted",
                )
            )
        ):
            await websocket.close(code=4401, reason="WebSocket token 无效")
            return
        token.consumed_at = now
        db.commit()
        logs = db.scalars(
            select(TaskLog)
            .join(AnalysisTask, AnalysisTask.id == TaskLog.task_id)
            .where(AnalysisTask.conversation_id == conversation_id)
            .order_by(TaskLog.created_at.desc())
            .limit(200)
        ).all()
        backlog = [json.loads(item.log_content) for item in reversed(logs)]

    await websocket_manager.connect(conversation_id, websocket)
    try:
        for event in backlog:
            await websocket.send_json(event)
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"event": "pong", "conversation_id": conversation_id})
    except WebSocketDisconnect:
        pass
    finally:
        await websocket_manager.disconnect(conversation_id, websocket)
