from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_user_id: str
    username: str
    display_name: str
    role: str
    status: str
    created_at: datetime


class ConversationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ConversationUpdate(BaseModel):
    conversation_id: int
    title: str = Field(min_length=1, max_length=255)


class ConversationDelete(BaseModel):
    conversation_ids: list[int] = Field(min_length=1)


class ConversationOut(BaseModel):
    conversation_id: int
    title: str
    status: str
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChatSend(BaseModel):
    conversation_id: int
    content: str = Field(min_length=1)
    attachment_ids: list[int] = Field(default_factory=list)
    scenario: Literal["auto", "catalog", "customer"] = "auto"


class AttachmentOut(BaseModel):
    attachment_id: int
    conversation_id: int
    message_id: int | None
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    parse_status: str
    created_at: datetime


class TaskOut(BaseModel):
    task_id: int
    conversation_id: int
    task_status: str
    current_step: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None


class MetricItem(BaseModel):
    metric_name: str
    metric_value: int | float | str
    metric_unit: str
    metric_period: str


class EvidenceItem(BaseModel):
    source_type: str
    source_name: str
    evidence_text: str
    related_metric: str
    confidence: float = Field(ge=0, le=1)


class ResultOut(BaseModel):
    result_id: int
    task_id: int
    problem_definition: str
    key_metrics: list[MetricItem]
    evidence_list: list[EvidenceItem]
    conclusion_text: str
    missing_data_text: str
    next_action_text: str
    result_markdown: str
    result_file_path: str | None
    created_at: datetime


class WebSocketTokenOut(BaseModel):
    websocket_token: str
    expires_in: int


class ConfigUpdate(BaseModel):
    config_value: str
    config_group: str = "general"


class DataSourceIn(BaseModel):
    name: str
    dialect: Literal["mysql", "sqlite", "postgresql"] = "mysql"
    connection_url: str
    status: Literal["active", "disabled"] = "active"


class ToolResult(BaseModel):
    tool_name: str
    status: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
