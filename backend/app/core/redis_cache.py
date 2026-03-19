"""Redis 캐시 래퍼 — Redis 장애 시 in-memory 폴백.

Redis 연결에 실패하면 in-memory dict + TTL 기반 캐시로 자동 전환하여
서비스 가용성을 유지한다. 폴백 시 경고 로그를 남긴다.

사용 예시:
    cache = RedisCache(settings.REDIS_URL)
    await cache.get("key")
    await cache.setex("key", ttl_seconds, "value")
    await cache.delete("key")
"""

import time
from dataclasses import dataclass
from typing import Optional

import redis.asyncio as aioredis

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _CacheEntry:
    value: str
    expires_at: float  # monotonic time


class _InMemoryFallback:
    """TTL-aware in-memory dict cache used when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}

    def _evict_expired(self, key: str) -> None:
        entry = self._store.get(key)
        if entry and time.monotonic() > entry.expires_at:
            del self._store[key]

    def get(self, key: str) -> Optional[str]:
        self._evict_expired(key)
        entry = self._store.get(key)
        return entry.value if entry else None

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = _CacheEntry(
            value=value, expires_at=time.monotonic() + ttl
        )

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


# Module-level singleton so fallback cache persists across requests
_fallback = _InMemoryFallback()
_redis_healthy: bool = True  # optimistic — assume Redis is up initially


def reset_fallback_cache() -> None:
    """테스트 격리를 위해 in-memory fallback 캐시를 초기화한다."""
    global _redis_healthy
    _fallback._store.clear()
    _redis_healthy = True


class RedisCache:
    """Redis-backed cache with automatic in-memory fallback on connection failure."""

    def __init__(self, redis_url: str) -> None:
        self._url = redis_url

    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값 조회. Redis 실패 시 in-memory 폴백."""
        global _redis_healthy
        try:
            async with aioredis.from_url(self._url, decode_responses=True) as r:
                value = await r.get(key)
                if not _redis_healthy:
                    logger.info("Redis connection restored")
                    _redis_healthy = True
                return value
        except Exception as e:
            if _redis_healthy:
                logger.warning(
                    "Redis unavailable, falling back to in-memory cache: %s", e
                )
                _redis_healthy = False
            return _fallback.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        """TTL을 지정하여 캐시에 값 저장. Redis 실패 시 in-memory 폴백."""
        global _redis_healthy
        try:
            async with aioredis.from_url(self._url, decode_responses=True) as r:
                await r.setex(key, ttl, value)
                if not _redis_healthy:
                    logger.info("Redis connection restored")
                    _redis_healthy = True
        except Exception as e:
            if _redis_healthy:
                logger.warning(
                    "Redis unavailable, falling back to in-memory cache: %s", e
                )
                _redis_healthy = False
            _fallback.setex(key, ttl, value)

    async def delete(self, key: str) -> None:
        """캐시에서 키 삭제. Redis 실패 시 in-memory 폴백."""
        global _redis_healthy
        try:
            async with aioredis.from_url(self._url, decode_responses=True) as r:
                await r.delete(key)
                if not _redis_healthy:
                    logger.info("Redis connection restored")
                    _redis_healthy = True
        except Exception as e:
            if _redis_healthy:
                logger.warning(
                    "Redis unavailable, falling back to in-memory cache: %s", e
                )
                _redis_healthy = False
            _fallback.delete(key)
