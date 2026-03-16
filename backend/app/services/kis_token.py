"""KIS (한국투자증권) OAuth2 access token lifecycle management.

KIS tokens are valid for 24 hours.
- Cached in Redis under key `kis:token:{app_key_hash}`
- Proactively rotated 10 minutes before expiry
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

import httpx
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_ROTATION_BUFFER_SECONDS = 600  # rotate 10 min before expiry
_TOKEN_TTL_SECONDS = 86400  # 24 h (KIS spec)


def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _cache_key_for(app_key: str) -> str:
    """Full app_key hash to prevent cross-user cache collision."""
    key_hash = hashlib.sha256(app_key.encode()).hexdigest()[:16]
    return f"kis:token:{key_hash}"


async def get_kis_access_token(app_key: str, app_secret: str) -> str:
    """Return a valid KIS access token, fetching from Redis cache or issuing a new one."""
    async with _get_redis() as redis:
        cache_key = _cache_key_for(app_key)
        cached = await redis.get(cache_key)
        if cached:
            return cached

        token = await _issue_token(app_key, app_secret)
        await redis.setex(
            cache_key,
            _TOKEN_TTL_SECONDS - _ROTATION_BUFFER_SECONDS,
            token,
        )
        return token


async def _issue_token(app_key: str, app_secret: str) -> str:
    """Call KIS token issuance endpoint and return the access token string."""
    url = f"{settings.KIS_BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        token: Optional[str] = data.get("access_token")
        if not token:
            raise ValueError("KIS token endpoint returned unexpected response format")
        return token


async def invalidate_kis_token(app_key: str) -> None:
    """Force evict the cached token so the next call will re-issue."""
    async with _get_redis() as redis:
        await redis.delete(_cache_key_for(app_key))
