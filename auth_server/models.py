from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthUser(Base):
    __tablename__ = "auth_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="analysis_user")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    codes: Mapped[list["OAuthCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OAuthCode(Base):
    __tablename__ = "oauth_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped[AuthUser] = relationship(back_populates="codes")
