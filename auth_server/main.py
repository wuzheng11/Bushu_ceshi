from __future__ import annotations

import html
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import jwt
from fastapi import Depends, FastAPI, Form, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal, get_db, init_db
from .models import AuthUser, OAuthCode
from .security import create_access_token, decode_access_token, hash_password, verify_password


def seed_users() -> None:
    with SessionLocal() as db:
        users = [
            {
                "external_user_id": "demo:analyst",
                "username": "analyst",
                "password": "analyst123",
                "display_name": "经营分析师",
                "role": "analysis_user",
            },
            {
                "external_user_id": "demo:admin",
                "username": "admin",
                "password": "admin123",
                "display_name": "系统管理员",
                "role": "admin",
            },
        ]
        changed = False
        for item in users:
            user = db.scalar(select(AuthUser).where(AuthUser.username == item["username"]))
            if not user:
                db.add(
                    AuthUser(
                        external_user_id=item["external_user_id"],
                        username=item["username"],
                        password_hash=hash_password(item["password"]),
                        display_name=item["display_name"],
                        role=item["role"],
                    )
                )
                changed = True
        if changed:
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_users()
    yield


app = FastAPI(title="本地 OAuth2 认证中心", version="1.0.0", lifespan=lifespan)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _error_html(message: str, status_code: int = 400) -> HTMLResponse:
    return HTMLResponse(
        f"""
        <!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
        <title>授权失败</title><style>
        body{{font-family:system-ui,sans-serif;background:#f4f6f8;display:grid;place-items:center;height:100vh}}
        main{{background:white;padding:32px;border:1px solid #d9dee5;border-radius:8px;max-width:560px}}
        a{{color:#136f63}}</style></head>
        <body><main><h1>授权失败</h1><p>{html.escape(message)}</p>
        <a href="http://localhost:5173">返回系统</a></main></body></html>
        """,
        status_code=status_code,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "local-oauth2-server"}


@app.get("/oauth/authorize", response_class=HTMLResponse)
def authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str = Query(...),
) -> HTMLResponse:
    if response_type != "code":
        return _error_html("仅支持 authorization_code 模式")
    if client_id != settings.client_id:
        return _error_html("client_id 不匹配", status.HTTP_401_UNAUTHORIZED)
    if redirect_uri != settings.allowed_redirect_uri:
        return _error_html("redirect_uri 未在白名单中")
    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="zh-CN">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <title>经营归因分析认证中心</title>
          <style>
            *{{box-sizing:border-box}}
            body{{margin:0;font-family:Inter,"Microsoft YaHei",system-ui,sans-serif;background:#f3f5f7;color:#17212b}}
            .shell{{min-height:100vh;display:grid;grid-template-columns:1.1fr .9fr}}
            .brand{{background:#123c36;color:white;padding:56px;display:flex;flex-direction:column;justify-content:space-between}}
            .brand h1{{font-size:38px;line-height:1.15;max-width:520px;margin:0}}
            .brand p{{font-size:16px;line-height:1.8;color:#c7ddd8;max-width:500px}}
            .panel{{display:grid;place-items:center;padding:40px}}
            form{{width:min(420px,100%);background:#fff;border:1px solid #dce2e7;border-radius:8px;padding:30px;box-shadow:0 16px 50px rgba(18,60,54,.08)}}
            h2{{margin:0 0 8px;font-size:24px}}.hint{{color:#66727e;margin:0 0 24px}}
            label{{font-size:13px;font-weight:700;display:block;margin:16px 0 7px}}
            input{{width:100%;height:42px;border:1px solid #bac4cd;border-radius:6px;padding:0 12px;font-size:15px}}
            button{{width:100%;height:44px;margin-top:22px;border:0;border-radius:6px;background:#136f63;color:#fff;font-size:15px;font-weight:700;cursor:pointer}}
            button:hover{{background:#0f5c52}}
            .demo{{margin-top:18px;padding:12px;background:#f3f7f6;border-radius:6px;color:#4c5b58;font-size:13px;line-height:1.8}}
          </style>
        </head>
        <body>
          <div class="shell">
            <section class="brand">
              <div><small>LOCAL OAUTH2</small><h1>经营归因分析系统</h1></div>
              <p>授权后，系统仅使用你的演示身份建立本地 JWT 会话，不会连接任何外部认证平台。</p>
            </section>
            <section class="panel">
              <form method="post" action="/oauth/approve">
                <h2>授权登录</h2>
                <p class="hint">使用内置演示账号进入分析工作台。</p>
                <input type="hidden" name="client_id" value="{html.escape(client_id)}">
                <input type="hidden" name="redirect_uri" value="{html.escape(redirect_uri)}">
                <input type="hidden" name="state" value="{html.escape(state)}">
                <label for="username">用户名</label>
                <input id="username" name="username" value="analyst" autocomplete="username" required>
                <label for="password">密码</label>
                <input id="password" name="password" type="password" value="analyst123" autocomplete="current-password" required>
                <button type="submit">同意授权并登录</button>
                <div class="demo">
                  分析用户：analyst / analyst123<br>
                  管理员：admin / admin123
                </div>
              </form>
            </section>
          </div>
        </body>
        </html>
        """
    )


@app.post("/oauth/approve")
def approve(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    state: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if client_id != settings.client_id or redirect_uri != settings.allowed_redirect_uri:
        return _error_html("客户端或回调地址校验失败")
    user = db.scalar(select(AuthUser).where(AuthUser.username == username))
    if not user or user.status != "active" or not verify_password(password, user.password_hash):
        return _error_html("用户名或密码错误", status.HTTP_401_UNAUTHORIZED)
    code = secrets.token_urlsafe(32)
    db.add(
        OAuthCode(
            code=code,
            client_id=client_id,
            user_id=user.id,
            redirect_uri=redirect_uri,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    db.commit()
    query = urlencode({"code": code, "state": state})
    return RedirectResponse(f"{redirect_uri}?{query}", status_code=status.HTTP_302_FOUND)


@app.post("/oauth/token")
def token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
) -> dict:
    if grant_type != "authorization_code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_grant_type")
    if client_id != settings.client_id or client_secret != settings.client_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_client")
    oauth_code = db.scalar(select(OAuthCode).where(OAuthCode.code == code))
    now = datetime.now(timezone.utc)
    if (
        not oauth_code
        or oauth_code.consumed_at is not None
        or _aware(oauth_code.expires_at) < now
        or oauth_code.redirect_uri != redirect_uri
        or oauth_code.client_id != client_id
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant")
    oauth_code.consumed_at = now
    user = db.get(AuthUser, oauth_code.user_id)
    db.commit()
    return {
        "access_token": create_access_token(user),
        "token_type": "Bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@app.get("/oauth/userinfo")
def userinfo(authorization: str = Header(...)) -> dict:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    try:
        claims = decode_access_token(authorization[7:].strip())
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc
    return {
        "sub": claims["sub"],
        "external_user_id": claims["external_user_id"],
        "username": claims["username"],
        "display_name": claims["display_name"],
        "role": claims["role"],
    }
