from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from auth_server.main import app as auth_app
from auth_server.security import decode_access_token


def test_authorization_code_flow() -> None:
    with TestClient(auth_app) as client:
        authorize = client.get(
            "/oauth/authorize",
            params={
                "response_type": "code",
                "client_id": "business-attribution-web",
                "redirect_uri": "http://localhost:8000/auth/callback",
                "state": "test-state",
            },
        )
        assert authorize.status_code == 200
        assert "同意授权并登录" in authorize.text

        approve = client.post(
            "/oauth/approve",
            data={
                "client_id": "business-attribution-web",
                "redirect_uri": "http://localhost:8000/auth/callback",
                "state": "test-state",
                "username": "analyst",
                "password": "analyst123",
            },
            follow_redirects=False,
        )
        assert approve.status_code == 302
        location = approve.headers["location"]
        query = parse_qs(urlparse(location).query)
        assert query["state"] == ["test-state"]
        code = query["code"][0]

        token_response = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:8000/auth/callback",
                "client_id": "business-attribution-web",
                "client_secret": "local-demo-secret",
            },
        )
        assert token_response.status_code == 200
        token = token_response.json()["access_token"]
        claims = decode_access_token(token)
        assert claims["username"] == "analyst"
        assert claims["role"] == "analysis_user"

        userinfo = client.get(
            "/oauth/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert userinfo.status_code == 200
        assert userinfo.json()["external_user_id"] == "demo:analyst"
