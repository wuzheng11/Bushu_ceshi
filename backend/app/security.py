from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status

from .config import settings


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "business-attribution-local",
        "aud": settings.auth_client_id,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.auth_client_id,
            issuer="business-attribution-local",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证无效或已过期",
        ) from exc
