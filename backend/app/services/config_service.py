from __future__ import annotations

import json
from threading import RLock
from typing import Any

from sqlalchemy import select

from ..database import SessionLocal
from ..models import SystemConfig


DEFAULT_CONFIGS: dict[str, tuple[str, str]] = {
    "analysis.default_scenario": ("auto", "analysis"),
    "analysis.max_database_rows": ("500", "analysis"),
    "analysis.min_impressions": ("1000", "analysis"),
    "analysis.low_ctr_threshold": ("0.035", "analysis"),
    "analysis.low_cvr_threshold": ("0.025", "analysis"),
    "analysis.enable_command_tool": ("true", "tool"),
    "analysis.enable_text_search": ("true", "tool"),
    "analysis.enable_llm_placeholder": ("true", "tool"),
    "system.export_format": ("markdown", "system"),
    "system.websocket_token_ttl_seconds": ("120", "system"),
    "feature.attachments": ("true", "feature"),
    "feature.command_tool": ("true", "feature"),
    "feature.result_export": ("true", "feature"),
}


class ConfigService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._cache: dict[str, str] = {}
        self._loaded = False

    def seed_defaults(self) -> None:
        with SessionLocal() as db:
            existing = {
                item.config_key: item
                for item in db.scalars(select(SystemConfig)).all()
            }
            changed = False
            for key, (value, group) in DEFAULT_CONFIGS.items():
                if key not in existing:
                    db.add(SystemConfig(config_key=key, config_value=value, config_group=group))
                    changed = True
            if changed:
                db.commit()
        self.reload()

    def reload(self) -> dict[str, str]:
        with SessionLocal() as db:
            rows = db.scalars(select(SystemConfig).order_by(SystemConfig.config_key)).all()
            loaded = {row.config_key: row.config_value for row in rows}
        with self._lock:
            self._cache = loaded or {key: value for key, (value, _) in DEFAULT_CONFIGS.items()}
            self._loaded = True
        return dict(self._cache)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.reload()

    def get(self, key: str, default: str | None = None) -> str | None:
        self._ensure_loaded()
        with self._lock:
            return self._cache.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def get_int(self, key: str, default: int) -> int:
        value = self.get(key)
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float) -> float:
        value = self.get(key)
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def get_json(self, key: str, default: Any) -> Any:
        value = self.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def all(self) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            rows = db.scalars(select(SystemConfig).order_by(SystemConfig.config_group, SystemConfig.config_key)).all()
            return [
                {
                    "config_key": row.config_key,
                    "config_value": row.config_value,
                    "config_group": row.config_group,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]

    def set(self, key: str, value: str, group: str = "general") -> SystemConfig:
        with SessionLocal() as db:
            row = db.scalar(select(SystemConfig).where(SystemConfig.config_key == key))
            if row:
                row.config_value = value
                row.config_group = group
            else:
                row = SystemConfig(config_key=key, config_value=value, config_group=group)
                db.add(row)
            db.commit()
            db.refresh(row)
            self.reload()
            return row


config_service = ConfigService()
