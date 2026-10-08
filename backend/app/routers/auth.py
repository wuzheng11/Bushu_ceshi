from __future__ import annotations

import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import UserOut
from ..security import create_access_token, decode_token


router = APIRouter(tags=["authentication"])


@router.get("/auth/login")
def auth_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.auth_client_id,
            "redirect_uri": f"{settings.backend_base_url}/auth/callback",
            "state": state,
        }
    )
    response = RedirectResponse(
        f"{settings.auth_public_url}/oauth/authorize?{query}",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        "oauth_state",
        state,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=600,
    )
    return response


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        return RedirectResponse(
            f"{settings.frontend_url}/login/callback?error={error}",
            status_code=status.HTTP_302_FOUND,
        )
    expected_state = request.cookies.get("oauth_state")
    if not code or not state or not expected_state or state != expected_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state 校验失败")

    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{settings.backend_base_url}/auth/callback",
        "client_id": settings.auth_client_id,
        "client_secret": settings.auth_client_secret,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                f"{settings.auth_server_url}/oauth/token",
                data=token_payload,
            )
        token_response.raise_for_status()
        provider_token = token_response.json()["access_token"]
        claims = decode_token(provider_token)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"认证中心令牌交换失败: {exc}",
        ) from exc

    username = claims.get("username") or claims.get("sub")
    external_user_id = claims.get("external_user_id") or f"external:{username}"
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        user = User(
            external_user_id=external_user_id,
            username=username,
            display_name=claims.get("display_name") or username,
            role=claims.get("role") or "analysis_user",
            status="active",
        )
        db.add(user)
    else:
        user.external_user_id = external_user_id
        user.display_name = claims.get("display_name") or user.display_name
        user.role = claims.get("role") or user.role
        user.status = "active"
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        subject=user.username,
        extra_claims={
            "username": user.username,
            "external_user_id": user.external_user_id,
            "display_name": user.display_name,
            "role": user.role,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    response = RedirectResponse(
        f"{settings.frontend_url}/login/callback?login=success",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.delete_cookie("oauth_state")
    return response


@router.get("/api/auth/me", response_model=UserOut)
def auth_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/api/auth/logout")
def auth_logout(response: Response) -> dict[str, str]:
    response.delete_cookie("access_token")
    return {"status": "ok"}
