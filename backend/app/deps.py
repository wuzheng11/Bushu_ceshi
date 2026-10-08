from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    payload = decode_token(token)
    username = payload.get("username") or payload.get("sub")
    user = db.scalar(select(User).where(User.username == username))
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


def get_owned_conversation_or_404(db: Session, conversation_id: int, user: User):
    from .models import Conversation

    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
            Conversation.status != "deleted",
        )
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return conversation
