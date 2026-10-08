from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _mysql_database_url(database: str) -> str:
    user = quote(os.getenv("MYSQL_USER", "root"), safe="")
    password = quote(os.getenv("MYSQL_PASSWORD", ""), safe="")
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    charset = os.getenv("MYSQL_CHARSET", "utf8mb4")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"


def _database_url() -> str:
    return os.getenv("AUTH_DATABASE_URL") or _mysql_database_url(
        os.getenv("AUTH_DB_NAME", "business_attribution_auth")
    )


@dataclass(frozen=True)
class AuthSettings:
    project_root: Path
    data_dir: Path
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    client_id: str
    client_secret: str
    allowed_redirect_uri: str
    access_token_expire_minutes: int

    @classmethod
    def from_env(cls) -> "AuthSettings":
        project_root = PROJECT_ROOT
        data_dir = Path(os.getenv("DATA_DIR", project_root / "data")).resolve()
        return cls(
            project_root=project_root,
            data_dir=data_dir,
            database_url=_database_url(),
            jwt_secret=os.getenv("JWT_SECRET", "dev-jwt-secret-change-me"),
            jwt_algorithm="HS256",
            client_id=os.getenv("AUTH_CLIENT_ID", "business-attribution-web"),
            client_secret=os.getenv("AUTH_CLIENT_SECRET", "local-demo-secret"),
            allowed_redirect_uri=os.getenv(
                "AUTH_REDIRECT_URI", "http://localhost:8000/auth/callback"
            ).rstrip("/"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")),
        )


settings = AuthSettings.from_env()
