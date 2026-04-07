"""USD/KRW FX rate utilities.

Provides fetch, cache, and DB snapshot functions for USD/KRW exchange rate.
Extracted from kis_price.py for file size reduction (TD-007).
"""

from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.core.redis_cache import RedisCache
from app.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

_cache = RedisCache(settings.REDIS_URL)

_FX_CACHE_KEY = "fx:USDKRW"
_FX_STALE_KEY = "fx:USDKRW:stale"
_FX_CACHE_TTL = 3600        # 1 hour (fresh)
_FX_STALE_TTL = 604800      # 7 days (stale fallback)
_FX_FALLBACK_RATE = Decimal("1450")


async def fetch_usd_krw_rate(
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
) -> Decimal:
    """USD/KRW 환율 조회. 1h 캐시 → frankfurter.app → 7일 stale 캐시 → 하드코딩 1450 순으로 fallback.

    KIS API에는 전용 환율 엔드포인트가 없으므로 ECB 기반 공개 FX API를 사용한다.
    API key 불필요, 무료, rate limit 없음.
    """
    cached = await _cache.get(_FX_CACHE_KEY)
    if cached:
        return Decimal(cached)

    try:
        resp = await client.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "KRW"},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        rate_str = str(data.get("rates", {}).get("KRW", "0"))
        if rate_str and rate_str != "0":
            rate = Decimal(rate_str)
            if rate > 100:
                await _cache.setex(_FX_CACHE_KEY, _FX_CACHE_TTL, str(rate))
                await _cache.setex(_FX_STALE_KEY, _FX_STALE_TTL, str(rate))
                logger.info("Fetched USD/KRW rate from frankfurter.app: %s", rate)
                return rate
    except Exception as e:
        logger.warning("Failed to fetch USD/KRW rate via frankfurter.app: %s", e)

    stale = await _cache.get(_FX_STALE_KEY)
    if stale:
        logger.info("Using stale cached USD/KRW rate: %s", stale)
        return Decimal(stale)

    logger.warning("Using hardcoded fallback USD/KRW rate: %s", _FX_FALLBACK_RATE)
    return _FX_FALLBACK_RATE


async def cache_fx_rate(rate: float) -> None:
    """외부 소스(TTTS3012R 잔고 API 등)에서 구한 환율을 Redis 캐시에 저장.

    sync 과정에서 wcrc_exrt 필드로 실제 환율을 얻었을 때 호출.
    """
    if rate <= 100:
        return  # 유효하지 않은 값
    rate_str = str(rate)
    await _cache.setex(_FX_CACHE_KEY, _FX_CACHE_TTL, rate_str)
    await _cache.setex(_FX_STALE_KEY, _FX_STALE_TTL, rate_str)
    logger.info("Cached USD/KRW rate from balance API: %s", rate_str)


async def get_cached_fx_rate() -> float:
    """캐시(Redis)에서만 USD/KRW 환율 조회. API 호출 없이 폴백 1450 반환.

    analytics 등 KIS 자격증명 없이 환율이 필요한 호출자용.
    """
    cached = await _cache.get(_FX_CACHE_KEY)
    if cached:
        return float(cached)
    stale = await _cache.get(_FX_STALE_KEY)
    if stale:
        return float(stale)
    return float(_FX_FALLBACK_RATE)


async def get_exchange_rate(app_key: str, app_secret: str) -> float:
    """USD/KRW 환율 조회 (캐시 우선, 실패 시 fallback 1350).

    sync.py 등 httpx 클라이언트 없이 환율만 필요한 호출자용 convenience wrapper.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        rate = await fetch_usd_krw_rate(app_key, app_secret, client)
    return float(rate)


async def save_fx_rate_snapshot(db: "AsyncSession", currency_pair: str, rate: float) -> bool:
    """환율 일별 스냅샷을 DB에 저장 (upsert).

    같은 날짜에 이미 저장된 경우 rate를 업데이트한다.
    성공 시 True, 실패 시 False 반환.
    """
    from app.models.fx_rate_snapshot import FxRateSnapshot

    today = date_type.today()
    try:
        stmt = pg_insert(FxRateSnapshot).values(
            currency_pair=currency_pair,
            rate=rate,
            snapshot_date=today,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fx_rate_snapshot_pair_date",
            set_={"rate": stmt.excluded.rate},
        )
        await db.execute(stmt)
        await db.commit()
        logger.info("Saved FX rate snapshot: %s = %s on %s", currency_pair, rate, today)
        return True
    except Exception as exc:
        logger.warning("Failed to save FX rate snapshot: %s", exc)
        await db.rollback()
        return False
