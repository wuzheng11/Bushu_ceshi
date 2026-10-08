from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
TEST_RUNTIME = Path(tempfile.mkdtemp(prefix="attribution-tests-"))

os.environ["DATA_DIR"] = str(TEST_RUNTIME / "data")
os.environ["UPLOADS_DIR"] = str(TEST_RUNTIME / "uploads")
os.environ["EXPORTS_DIR"] = str(TEST_RUNTIME / "exports")
os.environ["WORKSPACE_DIR"] = str(TEST_RUNTIME / "workspace")
os.environ["APP_DATABASE_URL"] = (
    f"sqlite:///{(TEST_RUNTIME / 'data' / 'app.db').as_posix()}"
)
os.environ["DEMO_DATABASE_URL"] = (
    f"sqlite:///{(TEST_RUNTIME / 'data' / 'demo.db').as_posix()}"
)
os.environ["AUTH_DATABASE_URL"] = (
    f"sqlite:///{(TEST_RUNTIME / 'data' / 'auth.db').as_posix()}"
)
os.environ["APP_SECRET_KEY"] = "test-app-secret"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from backend.app.database import SessionLocal  # noqa: E402
from backend.app.main import app as backend_app  # noqa: E402
from backend.app.models import User  # noqa: E402
from backend.app.security import create_access_token  # noqa: E402
from backend.app.seed import seed_application_data, seed_demo_data  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_data() -> None:
    seed_application_data()
    seed_demo_data(reset=True)


@pytest.fixture()
def client() -> TestClient:
    with TestClient(backend_app) as test_client:
        yield test_client


def _ensure_user(username: str, role: str) -> User:
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            user = User(
                external_user_id=f"test:{username}",
                username=username,
                display_name="测试分析用户" if role == "analysis_user" else "测试管理员",
                role=role,
                status="active",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user


@pytest.fixture()
def analyst_client(client: TestClient) -> TestClient:
    user = _ensure_user("test_analyst", "analysis_user")
    token = create_access_token(
        user.username,
        {"username": user.username, "role": user.role, "external_user_id": user.external_user_id},
    )
    client.cookies.set("access_token", token)
    return client


@pytest.fixture()
def admin_client(client: TestClient) -> TestClient:
    user = _ensure_user("test_admin", "admin")
    token = create_access_token(
        user.username,
        {"username": user.username, "role": user.role, "external_user_id": user.external_user_id},
    )
    client.cookies.set("access_token", token)
    return client
