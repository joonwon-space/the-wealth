"""Redis 캐시 래퍼 — Redis 장애 시 in-memory 폴백.

Redis 연결에 실패하면 in-memory dict + TTL 기반 캐시로 자동 전환하여
서비스 가용성을 유지한다. 폴백 시 경고 로그를 남긴다.

모듈 레벨 ConnectionPool 싱글턴을 통해 모든 캐시 작업이 동일한 TCP 연결
풀을 재사용한다. 이로 인해 요청마다 발생하는 40–300ms TCP 오버헤드가
제거된다.

사용 예시:
    cache = RedisCache(settings.REDIS_URL)
    await cache.get("key")
    await cache.setex("key", ttl_seconds, "value")
    await cache.delete("key")

    # 풀 공유 클라이언트 직접 사용 (security.py, dashboard.py 등):
    async with get_redis_client() as r:
        await r.set("key", "value")
"""

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import redis.asyncio as aioredis

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level ConnectionPool singleton — created once, shared across all
# callers in this process.  Initialized lazily on first use so that import
# order and test isolation are not affected.
# ---------------------------------------------------------------------------
_pool: Optional[aioredis.ConnectionPool] = None


def _get_pool(redis_url: str) -> aioredis.ConnectionPool:
    """Return the module-level pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _pool


@asynccontextmanager
async def get_redis_client(redis_url: str = "") -> AsyncIterator[aioredis.Redis]:
    """Yield a Redis client backed by the shared ConnectionPool.

    Callers do NOT need to close the client — the context manager handles it.
    Importing this avoids the per-request TCP handshake overhead of
    ``aioredis.from_url()``.

    Example::

        from app.core.redis_cache import get_redis_client
        from app.core.config import settings

        async with get_redis_client(settings.REDIS_URL) as r:
            await r.set("key", "value")
    """
    from app.core.config import settings  # avoid circular import at module level

    url = redis_url or settings.REDIS_URL
    pool = _get_pool(url)
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()


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

    def set_nx(self, key: str, ttl: int, value: str) -> bool:
        """Atomic SET-if-not-exists for in-memory fallback. Single-process only.

        Returns True if key did not exist (lock acquired), False otherwise.
        Expired entries are first evicted so they don't block re-acquisition.
        """
        self._evict_expired(key)
        if key in self._store:
            return False
        self._store[key] = _CacheEntry(
            value=value, expires_at=time.monotonic() + ttl
        )
        return True

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


# Module-level singleton so fallback cache persists across requests
_fallback = _InMemoryFallback()
_redis_healthy: bool = True  # optimistic — assume Redis is up initially


def reset_fallback_cache() -> None:
    """테스트 격리를 위해 in-memory fallback 캐시와 ConnectionPool을 초기화한다."""
    global _redis_healthy, _pool
    _fallback._store.clear()
    _redis_healthy = True
    _pool = None  # force pool re-creation in tests to avoid cross-test state


class RedisCache:
    """Redis-backed cache with automatic in-memory fallback on connection failure.

    Uses the module-level ConnectionPool singleton so all instances share the
    same pool — no new TCP connection per operation.
    """

    def __init__(self, redis_url: str) -> None:
        self._url = redis_url

    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값 조회. Redis 실패 시 in-memory 폴백."""
        global _redis_healthy
        try:
            async with get_redis_client(self._url) as r:
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
            async with get_redis_client(self._url) as r:
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
            async with get_redis_client(self._url) as r:
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

    async def set_nx(self, key: str, ttl: int, value: str = "1") -> bool:
        """Atomic SETNX (SET if Not eXists) with TTL — distributed lock primitive.

        Returns True if the key was set (caller is leader), False if it already
        existed (caller is follower). Used for single-flight request coalescing
        so N concurrent KIS lookups for the same ticker collapse to 1.

        Redis 실패 시 in-memory fallback. 멀티 워커에서 fallback 동작 시 워커
        간 동시성은 막을 수 없지만 워커 내 동시성은 차단된다.
        """
        global _redis_healthy
        try:
            async with get_redis_client(self._url) as r:
                # redis SET key value NX EX ttl — atomic, returns True if set
                result = await r.set(key, value, nx=True, ex=ttl)
                if not _redis_healthy:
                    logger.info("Redis connection restored")
                    _redis_healthy = True
                return bool(result)
        except Exception as e:
            if _redis_healthy:
                logger.warning(
                    "Redis unavailable, falling back to in-memory cache: %s", e
                )
                _redis_healthy = False
            return _fallback.set_nx(key, ttl, value)
