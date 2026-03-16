from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import redis.asyncio as aioredis
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_REFRESH_TOKEN_PREFIX = "refresh_jti:"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(UTC) + expires_delta}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Create refresh token with a unique jti. Returns (token, jti)."""
    jti = str(uuid.uuid4())
    token = _create_token(
        {"sub": str(user_id), "type": "refresh", "jti": jti},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return token, jti


async def store_refresh_jti(jti: str, user_id: int) -> None:
    """Store refresh token jti in Redis with TTL matching token lifetime."""
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
        await r.setex(f"{_REFRESH_TOKEN_PREFIX}{jti}", ttl, str(user_id))


async def verify_and_consume_refresh_jti(jti: str) -> Optional[int]:
    """Verify jti exists in Redis, consume it (delete), return user_id or None."""
    async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
        user_id_str = await r.get(f"{_REFRESH_TOKEN_PREFIX}{jti}")
        if user_id_str is None:
            return None
        await r.delete(f"{_REFRESH_TOKEN_PREFIX}{jti}")
        return int(user_id_str)


async def revoke_all_refresh_tokens_for_user(user_id: int) -> None:
    """Revoke all refresh tokens for a user (on logout/password change)."""
    async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor, match=f"{_REFRESH_TOKEN_PREFIX}*", count=100)
            for key in keys:
                val = await r.get(key)
                if val == str(user_id):
                    await r.delete(key)
            if cursor == 0:
                break


def decode_access_token(token: str) -> Optional[int]:
    """Returns user_id if token is a valid access token, else None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        sub = payload.get("sub")
        return int(sub) if sub else None
    except (JWTError, ValueError):
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """Returns {user_id, jti} if token is a valid refresh token, else None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        sub = payload.get("sub")
        jti = payload.get("jti")
        if not sub or not jti:
            return None
        return {"user_id": int(sub), "jti": jti}
    except (JWTError, ValueError):
        return None
