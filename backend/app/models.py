from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="analysis_user")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("idx_conversations_user_status", "user_id", "status", "updated_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["AnalysisTask"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["ContextSummary"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq_no", name="uq_message_sequence"),
        Index("idx_messages_conversation_seq", "conversation_id", "seq_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_name: Mapped[Optional[str]] = mapped_column(String(128))
    tool_status: Mapped[Optional[str]] = mapped_column(String(32))
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="message")


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (Index("idx_attachments_conversation", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="attachments")
    message: Mapped[Optional[Message]] = relationship(back_populates="attachments")


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"
    __table_args__ = (Index("idx_tasks_conversation_status", "conversation_id", "task_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    task_status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    current_step: Mapped[Optional[str]] = mapped_column(String(128))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    conversation: Mapped[Conversation] = relationship(back_populates="tasks")
    result: Mapped[Optional["AnalysisResult"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )
    logs: Mapped[list["TaskLog"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (Index("idx_results_conversation", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    problem_definition: Mapped[str] = mapped_column(Text, nullable=False)
    key_metrics_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_list_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    conclusion_text: Mapped[str] = mapped_column(Text, nullable=False)
    missing_data_text: Mapped[str] = mapped_column(Text, nullable=False)
    next_action_text: Mapped[str] = mapped_column(Text, nullable=False)
    result_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    result_file_path: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    task: Mapped[AnalysisTask] = relationship(back_populates="result")
    conversation: Mapped[Conversation] = relationship(back_populates="results")


class ContextSummary(Base):
    __tablename__ = "context_summaries"
    __table_args__ = (Index("idx_summaries_conversation", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    start_seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    end_seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="summaries")


class WebSocketToken(Base):
    __tablename__ = "websocket_tokens"
    __table_args__ = (Index("idx_ws_tokens_lookup", "token", "expires_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    config_group: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class TaskLog(Base):
    __tablename__ = "task_logs"
    __table_args__ = (Index("idx_task_logs_task", "task_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False
    )
    log_level: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    log_type: Mapped[str] = mapped_column(String(64), nullable=False)
    log_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    task: Mapped[AnalysisTask] = relationship(back_populates="logs")


class DataSourceConnection(Base):
    __tablename__ = "data_source_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    dialect: Mapped[str] = mapped_column(String(32), nullable=False, default="mysql")
    connection_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
