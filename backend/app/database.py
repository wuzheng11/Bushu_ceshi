from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


settings.ensure_directories()


def create_database_engine(database_url: str) -> Engine:
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    options: dict[str, Any] = {"pool_pre_ping": True}
    if database_url.startswith("mysql"):
        options["pool_recycle"] = 3600
    return create_engine(database_url, connect_args=connect_args, **options)


engine = create_database_engine(settings.app_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
