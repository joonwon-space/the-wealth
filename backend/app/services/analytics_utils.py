"""공통 analytics 유틸리티 — 캐시 키, 기간 계산, 캐시 무효화."""

from datetime import date as date_type, timedelta
from typing import Optional

from app.core.config import settings
from app.core.redis_cache import RedisCache

_analytics_cache = RedisCache(settings.REDIS_URL)
ANALYTICS_CACHE_TTL = 3600  # 1시간; sync 시 무효화


def analytics_key(user_id: int, endpoint: str) -> str:
    return f"analytics:{user_id}:{endpoint}"


def period_cutoff(period: str) -> Optional[date_type]:
    """Return the earliest date for the given period, or None for ALL."""
    today = date_type.today()
    if period == "1W":
        return today - timedelta(days=7)
    if period == "1M":
        return today - timedelta(days=30)
    if period == "3M":
        return today - timedelta(days=91)
    if period == "6M":
        return today - timedelta(days=182)
    if period == "1Y":
        return today - timedelta(days=365)
    return None  # ALL


async def invalidate_analytics_cache(user_id: int) -> None:
    """sync 성공 후 호출 — 해당 유저의 분석 캐시 전체 삭제."""
    for endpoint in ("metrics", "monthly-returns", "sector-allocation", "fx-gain-loss"):
        await _analytics_cache.delete(analytics_key(user_id, endpoint))
    # period-specific keys for portfolio-history and krw-asset-history
    for period in ("1W", "1M", "3M", "6M", "1Y", "ALL"):
        await _analytics_cache.delete(analytics_key(user_id, f"portfolio-history:{period}"))
    for period in ("1M", "3M", "6M", "1Y", "ALL"):
        await _analytics_cache.delete(analytics_key(user_id, f"krw-asset-history:{period}"))


def get_analytics_cache() -> RedisCache:
    """Shared analytics Redis cache instance."""
    return _analytics_cache
