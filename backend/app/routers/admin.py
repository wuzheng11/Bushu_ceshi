from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import create_database_engine, get_db
from ..deps import require_admin
from ..models import AnalysisTask, DataSourceConnection, TaskLog, User
from ..schemas import ConfigUpdate, DataSourceIn
from ..services.config_service import config_service


router = APIRouter(tags=["admin"])


@router.post("/api/admin/reload")
def reload_config(_: User = Depends(require_admin)) -> dict[str, str]:
    loaded = config_service.reload()
    return {"status": "ok", "message": f"配置已热更新，共加载 {len(loaded)} 项"}


@router.get("/api/admin/configs")
def list_configs(_: User = Depends(require_admin)) -> list[dict]:
    return config_service.all()


@router.put("/api/admin/configs/{config_key}")
def update_config(
    config_key: str,
    payload: ConfigUpdate,
    _: User = Depends(require_admin),
) -> dict:
    row = config_service.set(config_key, payload.config_value, payload.config_group)
    return {
        "config_key": row.config_key,
        "config_value": row.config_value,
        "config_group": row.config_group,
        "updated_at": row.updated_at,
    }


@router.get("/api/admin/logs")
def list_logs(
    task_id: int | None = None,
    log_level: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(TaskLog).order_by(TaskLog.created_at.desc()).limit(limit)
    if task_id is not None:
        query = query.where(TaskLog.task_id == task_id)
    if log_level:
        query = query.where(TaskLog.log_level == log_level.upper())
    logs = db.scalars(query).all()
    task_conversations = {
        task.id: task.conversation_id
        for task in db.scalars(
            select(AnalysisTask).where(AnalysisTask.id.in_([item.task_id for item in logs]))
        ).all()
    }
    return [
        {
            "id": item.id,
            "task_id": item.task_id,
            "conversation_id": task_conversations.get(item.task_id),
            "log_level": item.log_level,
            "log_type": item.log_type,
            "log_content": item.log_content,
            "created_at": item.created_at,
        }
        for item in logs
    ]


@router.get("/api/admin/data-sources")
def list_data_sources(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(select(DataSourceConnection).order_by(DataSourceConnection.id)).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "dialect": row.dialect,
            "connection_url": row.connection_url,
            "status": row.status,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.post("/api/admin/data-sources")
def create_data_source(
    payload: DataSourceIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    if db.scalar(select(DataSourceConnection).where(DataSourceConnection.name == payload.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="数据源名称已存在")
    row = DataSourceConnection(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "status": row.status}


@router.put("/api/admin/data-sources/{source_id}")
def update_data_source(
    source_id: int,
    payload: DataSourceIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(DataSourceConnection, source_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return {"id": row.id, "name": row.name, "status": row.status}


@router.post("/api/admin/data-sources/{source_id}/test")
def test_data_source(
    source_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(DataSourceConnection, source_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")
    from sqlalchemy import text

    try:
        engine = create_database_engine(row.connection_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "message": "连接测试成功"}
    except Exception as exc:
        return {"status": "failed", "message": str(exc)}


@router.get("/api/configs/public")
def public_configs(user: User = Depends(require_admin)) -> dict:
    return {
        "role": user.role,
        "features": {
            "attachments": config_service.get_bool("feature.attachments", True),
            "command_tool": config_service.get_bool("feature.command_tool", True),
            "result_export": config_service.get_bool("feature.result_export", True),
        },
        "websocket_token_ttl_seconds": config_service.get_int(
            "system.websocket_token_ttl_seconds", 120
        ),
    }
