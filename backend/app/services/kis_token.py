"""KIS (한국투자증권) OAuth2 access token lifecycle management.

KIS tokens are valid for 24 hours.
- Cached in Redis under key `kis:token:{app_key_hash}`
- TTL derived from `access_token_token_expired` in the issuance response (KST)
- Application-layer expiry check prevents serving stale tokens even if Redis TTL is wrong
- Proactively rotated 10 minutes before expiry
"""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_cache import RedisCache
from app.services.kis_rate_limiter import acquire_token_issuance

logger = get_logger(__name__)

_ROTATION_BUFFER_SECONDS = 600  # rotate 10 min before expiry
_TOKEN_TTL_SECONDS = 86400  # 24 h fallback (KIS spec)
_KST = timezone(timedelta(hours=9))  # KIS expiry strings are KST

# Cache value format: "{token}:::{unix_expiry_timestamp}"
# Legacy entries (plain string) are returned as-is for backward compatibility.
_SEPARATOR = ":::"

_cache = RedisCache(settings.REDIS_URL)

# Per-key locks prevent concurrent coroutines from issuing duplicate tokens.
_issue_locks: dict[str, asyncio.Lock] = {}
_issue_locks_guard: asyncio.Lock = asyncio.Lock()


def _cache_key_for(app_key: str) -> str:
    """Full app_key hash to prevent cross-user cache collision."""
    key_hash = hashlib.sha256(app_key.encode()).hexdigest()[:16]
    return f"kis:token:{key_hash}"


async def _get_issue_lock(cache_key: str) -> asyncio.Lock:
    async with _issue_locks_guard:
        if cache_key not in _issue_locks:
            _issue_locks[cache_key] = asyncio.Lock()
        return _issue_locks[cache_key]


def _parse_cached(cached: str) -> tuple[str, bool]:
    """Parse cached value and validate application-layer expiry.

    Returns (token, is_valid). is_valid=False means the token is within
    the rotation buffer window and should be evicted and reissued.
    """
    if _SEPARATOR not in cached:
        # Legacy format (plain token string) — assume valid, no expiry info.
        return cached, True

    token_val, exp_str = cached.split(_SEPARATOR, 1)
    try:
        expires_at = float(exp_str)
        is_valid = expires_at > time.time() + _ROTATION_BUFFER_SECONDS
        return token_val, is_valid
    except ValueError:
        # Malformed expiry — return as-is and let Redis TTL handle eviction.
        return token_val, True


async def get_kis_access_token(app_key: str, app_secret: str) -> str:
    """Return a valid KIS access token, fetching from cache or issuing a new one.

    Uses double-checked locking: fast cache read first, then per-key lock to
    prevent concurrent coroutines from each issuing a new token on cache miss.

    Application-layer expiry validation ensures stale tokens are evicted even
    if the Redis TTL was set incorrectly (e.g., due to timezone mismatches).
    """
    cache_key = _cache_key_for(app_key)

    # Fast path — cache hit with valid expiry.
    cached = await _cache.get(cache_key)
    if cached:
        token, valid = _parse_cached(cached)
        if valid:
            return token
        logger.info("KIS token near/past expiry (app-layer check), evicting and reissuing")
        await _cache.delete(cache_key)

    # Slow path — acquire per-key lock so only one coroutine issues a token.
    lock = await _get_issue_lock(cache_key)
    async with lock:
        # Re-check: another coroutine may have populated the cache while we waited.
        cached = await _cache.get(cache_key)
        if cached:
            token, valid = _parse_cached(cached)
            if valid:
                return token
            await _cache.delete(cache_key)

        token, ttl, expires_at_unix = await _issue_token(app_key, app_secret)
        cache_value = f"{token}{_SEPARATOR}{expires_at_unix}"
        await _cache.setex(cache_key, max(ttl - _ROTATION_BUFFER_SECONDS, 60), cache_value)
        return token


async def _issue_token(app_key: str, app_secret: str) -> tuple[str, int, float]:
    """Call KIS token issuance endpoint and return (access_token, ttl_seconds, expires_at_unix)."""
    url = f"{settings.KIS_BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    await acquire_token_issuance()
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Re-raise without request/response objects to prevent KIS credentials
            # from leaking into Sentry via the httpx exception chain.
            raise RuntimeError(
                f"KIS token endpoint returned HTTP {exc.response.status_code}"
            ) from None
        data = resp.json()

    token: Optional[str] = data.get("access_token")
    if not token:
        raise ValueError("KIS token endpoint returned unexpected response format")

    # Default: 24h fallback
    ttl = _TOKEN_TTL_SECONDS
    expires_at_unix = time.time() + _TOKEN_TTL_SECONDS

    expires_str: Optional[str] = data.get("access_token_token_expired")
    if expires_str:
        try:
            # KIS returns expiry in KST (e.g. "2026-04-22 13:47:51").
            # Must attach KST tzinfo before comparing with UTC-based time.time().
            expires_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_KST)
            expires_at_unix = expires_dt.timestamp()
            ttl = max(int(expires_at_unix - time.time()), 60)
        except (ValueError, OverflowError):
            logger.warning(
                "Could not parse KIS token expiry '%s', using default TTL", expires_str
            )

    logger.info(
        "KIS token issued, TTL=%ds (expires=%s KST)", ttl, expires_str
    )
    return token, ttl, expires_at_unix


async def invalidate_kis_token(app_key: str) -> None:
    """Force evict the cached token so the next call will re-issue."""
    await _cache.delete(_cache_key_for(app_key))
