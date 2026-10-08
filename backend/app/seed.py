from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url

from .config import settings
from .database import SessionLocal, create_database_engine, init_db
from .models import DataSourceConnection
from .services.config_service import config_service


DEMO_TABLES: dict[str, list[tuple[str, str]]] = {
    "category_master": [
        ("category_id", "INTEGER PRIMARY KEY"),
        ("category_name", "TEXT NOT NULL"),
        ("attribute_completeness", "REAL NOT NULL"),
        ("is_priority", "INTEGER NOT NULL DEFAULT 0"),
    ],
    "product_master": [
        ("product_id", "INTEGER PRIMARY KEY"),
        ("product_name", "TEXT NOT NULL"),
        ("category_id", "INTEGER NOT NULL"),
        ("price", "REAL NOT NULL"),
        ("status", "TEXT NOT NULL"),
    ],
    "search_impressions": [
        ("id", "INTEGER PRIMARY KEY"),
        ("product_id", "INTEGER NOT NULL"),
        ("impression_date", "TEXT NOT NULL"),
        ("impressions", "INTEGER NOT NULL"),
        ("search_term", "TEXT NOT NULL"),
    ],
    "product_clicks": [
        ("id", "INTEGER PRIMARY KEY"),
        ("product_id", "INTEGER NOT NULL"),
        ("click_date", "TEXT NOT NULL"),
        ("clicks", "INTEGER NOT NULL"),
    ],
    "product_conversions": [
        ("id", "INTEGER PRIMARY KEY"),
        ("product_id", "INTEGER NOT NULL"),
        ("order_date", "TEXT NOT NULL"),
        ("orders", "INTEGER NOT NULL"),
        ("gmv", "REAL NOT NULL"),
    ],
    "business_users": [
        ("user_id", "INTEGER PRIMARY KEY"),
        ("username", "TEXT NOT NULL"),
        ("city", "TEXT NOT NULL"),
        ("channel", "TEXT NOT NULL"),
        ("registered_at", "TEXT NOT NULL"),
    ],
    "visit_events": [
        ("event_id", "INTEGER PRIMARY KEY"),
        ("user_id", "INTEGER NOT NULL"),
        ("session_id", "TEXT NOT NULL"),
        ("event_time", "TEXT NOT NULL"),
        ("page_type", "TEXT NOT NULL"),
        ("channel", "TEXT NOT NULL"),
    ],
    "add_cart_events": [
        ("event_id", "INTEGER PRIMARY KEY"),
        ("user_id", "INTEGER NOT NULL"),
        ("session_id", "TEXT NOT NULL"),
        ("event_time", "TEXT NOT NULL"),
        ("product_id", "INTEGER NOT NULL"),
        ("quantity", "INTEGER NOT NULL"),
        ("price", "REAL NOT NULL"),
    ],
    "order_events": [
        ("event_id", "INTEGER PRIMARY KEY"),
        ("user_id", "INTEGER NOT NULL"),
        ("session_id", "TEXT NOT NULL"),
        ("event_time", "TEXT NOT NULL"),
        ("order_id", "TEXT NOT NULL"),
        ("amount", "REAL NOT NULL"),
        ("status", "TEXT NOT NULL"),
    ],
}

INTEGER_COLUMNS = {
    "category_id",
    "is_priority",
    "product_id",
    "id",
    "impressions",
    "clicks",
    "orders",
    "user_id",
    "event_id",
    "quantity",
}
FLOAT_COLUMNS = {"attribute_completeness", "price", "gmv", "amount"}


def _convert_value(column: str, value: str) -> Any:
    if value == "":
        return None
    if column in INTEGER_COLUMNS:
        return int(value)
    if column in FLOAT_COLUMNS:
        return float(value)
    return value


def create_demo_tables(engine) -> None:
    with engine.begin() as connection:
        dialect = connection.dialect.name
        for table_name, columns in DEMO_TABLES.items():
            definitions = []
            for name, kind in columns:
                if dialect == "mysql" and kind == "INTEGER PRIMARY KEY":
                    definitions.append(f"{name} INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY")
                else:
                    definitions.append(f"{name} {kind}")
            columns_sql = ", ".join(definitions)
            table_options = (
                " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
                if dialect == "mysql"
                else ""
            )
            connection.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {table_name} "
                    f"({columns_sql}){table_options}"
                )
            )


def seed_demo_data(reset: bool = True) -> None:
    settings.ensure_directories()
    engine = create_database_engine(settings.demo_database_url)
    create_demo_tables(engine)
    sample_root = settings.project_root / "sample_data"
    files = [
        sample_root / "scenario_a" / "category_master.csv",
        sample_root / "scenario_a" / "product_master.csv",
        sample_root / "scenario_a" / "search_impressions.csv",
        sample_root / "scenario_a" / "product_clicks.csv",
        sample_root / "scenario_a" / "product_conversions.csv",
        sample_root / "scenario_b" / "business_users.csv",
        sample_root / "scenario_b" / "visit_events.csv",
        sample_root / "scenario_b" / "add_cart_events.csv",
        sample_root / "scenario_b" / "order_events.csv",
    ]
    with engine.begin() as connection:
        if reset:
            for table_name in reversed(list(DEMO_TABLES)):
                connection.execute(text(f"DELETE FROM {table_name}"))
        for file_path in files:
            table_name = file_path.stem
            with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                if not rows:
                    continue
                columns = list(rows[0].keys())
                placeholders = ", ".join(f":{column}" for column in columns)
                column_sql = ", ".join(columns)
                statement = text(
                    f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})"
                )
                connection.execute(
                    statement,
                    [
                        {column: _convert_value(column, row[column]) for column in columns}
                        for row in rows
                    ],
                )


def demo_data_loaded(engine) -> bool:
    with engine.connect() as connection:
        for table_name in DEMO_TABLES:
            count = connection.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar_one()
            if int(count or 0) == 0:
                return False
    return True


def seed_demo_data_if_needed() -> None:
    settings.ensure_directories()
    engine = create_database_engine(settings.demo_database_url)
    try:
        create_demo_tables(engine)
        if demo_data_loaded(engine):
            print("演示业务数据已存在，跳过重复导入。")
            return
        seed_demo_data(reset=True)
    finally:
        engine.dispose()


def seed_application_data() -> None:
    init_db()
    config_service.seed_defaults()
    with SessionLocal() as db:
        if not db.query(DataSourceConnection).filter_by(name="经营演示数据集").first():
            dialect = make_url(settings.demo_database_url).get_backend_name()
            db.add(
                DataSourceConnection(
                    name="经营演示数据集",
                    dialect=dialect,
                    connection_url=settings.demo_database_url,
                    status="active",
                )
            )
            db.commit()


def seed_if_needed() -> None:
    seed_application_data()
    seed_demo_data_if_needed()


def main() -> None:
    seed_application_data()
    seed_demo_data(reset=True)
    app_url = make_url(settings.app_database_url).render_as_string(hide_password=True)
    demo_url = make_url(settings.demo_database_url).render_as_string(hide_password=True)
    print(f"应用数据库初始化完成: {app_url}")
    print(f"演示业务数据库初始化完成: {demo_url}")


if __name__ == "__main__":
    main()
