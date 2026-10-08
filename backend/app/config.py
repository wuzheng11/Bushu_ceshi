from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _mysql_database_url(database: str) -> str:
    user = quote(os.getenv("MYSQL_USER", "root"), safe="")
    password = quote(os.getenv("MYSQL_PASSWORD", ""), safe="")
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    charset = os.getenv("MYSQL_CHARSET", "utf8mb4")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"


def _database_url(url_env: str, database_env: str, default_database: str) -> str:
    return os.getenv(url_env) or _mysql_database_url(
        os.getenv(database_env, default_database)
    )


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    uploads_dir: Path
    exports_dir: Path
    workspace_dir: Path
    app_database_url: str
    demo_database_url: str
    app_secret_key: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    backend_base_url: str
    frontend_url: str
    auth_server_url: str
    auth_public_url: str
    auth_client_id: str
    auth_client_secret: str
    cookie_secure: bool

    @classmethod
    def from_env(cls) -> "Settings":
        project_root = PROJECT_ROOT
        data_dir = Path(os.getenv("DATA_DIR", project_root / "data")).resolve()
        uploads_dir = Path(os.getenv("UPLOADS_DIR", project_root / "uploads")).resolve()
        exports_dir = Path(os.getenv("EXPORTS_DIR", project_root / "exports")).resolve()
        workspace_dir = Path(os.getenv("WORKSPACE_DIR", project_root / "workspace")).resolve()
        app_database_url = _database_url(
            "APP_DATABASE_URL",
            "APP_DB_NAME",
            "business_attribution_app",
        )
        demo_database_url = _database_url(
            "DEMO_DATABASE_URL",
            "DEMO_DB_NAME",
            "business_attribution_demo",
        )
        auth_server_url = os.getenv(
            "AUTH_SERVER_URL", "http://localhost:8001"
        ).rstrip("/")
        auth_public_url = os.getenv("AUTH_PUBLIC_URL", auth_server_url).rstrip("/")

        return cls(
            project_root=project_root,
            data_dir=data_dir,
            uploads_dir=uploads_dir,
            exports_dir=exports_dir,
            workspace_dir=workspace_dir,
            app_database_url=app_database_url,
            demo_database_url=demo_database_url,
            app_secret_key=os.getenv("APP_SECRET_KEY", "dev-app-secret-change-me"),
            jwt_secret=os.getenv("JWT_SECRET", "dev-jwt-secret-change-me"),
            jwt_algorithm="HS256",
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")),
            backend_base_url=os.getenv("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/"),
            frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/"),
            auth_server_url=auth_server_url,
            auth_public_url=auth_public_url,
            auth_client_id=os.getenv("AUTH_CLIENT_ID", "business-attribution-web"),
            auth_client_secret=os.getenv("AUTH_CLIENT_SECRET", "local-demo-secret"),
            cookie_secure=os.getenv("COOKIE_SECURE", "false").strip().lower()
            in {"1", "true", "yes", "on"},
        )

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.uploads_dir,
            self.exports_dir,
            self.workspace_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings.from_env()
