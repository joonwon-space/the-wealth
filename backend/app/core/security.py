import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.redis_cache import get_redis_client

# Key format: refresh:{user_id}:{jti}
# Enables O(1) per-user revocation via SCAN refresh:{user_id}:*
# instead of the prior O(N) global scan over all refresh keys.
_REFRESH_TOKEN_PREFIX = "refresh:"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(UTC) + expires_delta}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


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


def _refresh_key(user_id: int, jti: str) -> str:
    """Build Redis key for a refresh token: refresh:{user_id}:{jti}."""
    return f"{_REFRESH_TOKEN_PREFIX}{user_id}:{jti}"


async def store_refresh_jti(jti: str, user_id: int) -> None:
    """Store refresh token jti in Redis with TTL matching token lifetime."""
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    value = json.dumps({"user_id": user_id, "created_at": datetime.now(UTC).isoformat()})
    async with get_redis_client(settings.REDIS_URL) as r:
        await r.setex(_refresh_key(user_id, jti), ttl, value)


async def verify_and_consume_refresh_jti(jti: str, user_id: int) -> bool:
    """Verify jti exists in Redis for user_id, consume it (delete). Returns True if valid."""
    key = _refresh_key(user_id, jti)
    async with get_redis_client(settings.REDIS_URL) as r:
        raw = await r.get(key)
        if raw is None:
            return False
        await r.delete(key)
        return True


async def list_sessions_for_user(user_id: int) -> list[dict]:
    """Return all active sessions for a user from Redis.

    Each session dict contains: jti, created_at (ISO string).
    Keys follow refresh:{user_id}:{jti} format.
    """
    sessions: list[dict] = []
    async with get_redis_client(settings.REDIS_URL) as r:
        cursor = 0
        while True:
            cursor, keys = await r.scan(
                cursor, match=f"{_REFRESH_TOKEN_PREFIX}{user_id}:*", count=100
            )
            for key in keys:
                raw = await r.get(key)
                if raw is None:
                    continue
                try:
                    data = json.loads(raw)
                except (ValueError, TypeError):
                    data = {}
                # Extract jti from key suffix: refresh:{user_id}:{jti}
                key_str = key if isinstance(key, str) else key.decode()
                prefix = f"{_REFRESH_TOKEN_PREFIX}{user_id}:"
                jti = key_str[len(prefix):] if key_str.startswith(prefix) else key_str
                sessions.append(
                    {
                        "jti": jti,
                        "created_at": data.get("created_at"),
                    }
                )
            if cursor == 0:
                break
    return sessions


async def revoke_session_for_user(user_id: int, jti: str) -> bool:
    """Revoke a specific session (jti) for a user. Returns True if found and deleted."""
    key = _refresh_key(user_id, jti)
    async with get_redis_client(settings.REDIS_URL) as r:
        deleted = await r.delete(key)
        return bool(deleted)


async def revoke_all_refresh_tokens_for_user(user_id: int) -> None:
    """Revoke all refresh tokens for a user (on logout/password change).

    Uses per-user key prefix refresh:{user_id}:* for O(1) targeted scan
    instead of global O(N) scan over all refresh keys.
    """
    async with get_redis_client(settings.REDIS_URL) as r:
        cursor = 0
        while True:
            cursor, keys = await r.scan(
                cursor, match=f"{_REFRESH_TOKEN_PREFIX}{user_id}:*", count=100
            )
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break


def decode_access_token(token: str) -> Optional[int]:
    """Returns user_id if token is a valid access token, else None."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        sub = payload.get("sub")
        return int(sub) if sub else None
    except (InvalidTokenError, ValueError):
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """Returns {user_id, jti} if token is a valid refresh token, else None."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        sub = payload.get("sub")
        jti = payload.get("jti")
        if not sub or not jti:
            return None
        return {"user_id": int(sub), "jti": jti}
    except (InvalidTokenError, ValueError):
        return None
