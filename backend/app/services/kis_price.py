"""KIS 현재가 조회 서비스 (국내 + 해외주식, asyncio.gather 병렬 처리).

Redis에 마지막 조회 가격을 캐싱(TTL: 시장 개장 중 5분 / 장 마감 후 24시간)하여
KIS API 장애 시 폴백.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_cache import RedisCache
from app.services.kis_health import get_kis_availability, set_kis_availability
from app.services.kis_rate_limiter import kis_call_slot
from app.services.kis_retry import kis_get
from app.services.kis_token import get_kis_access_token

# FX utilities extracted to kis_fx.py — re-exported here for backward compatibility
from app.services.kis_fx import (  # noqa: F401
    cache_fx_rate,
    fetch_usd_krw_rate,
    get_cached_fx_rate,
    get_exchange_rate,
    save_fx_rate_snapshot,
    _FX_CACHE_KEY,
    _FX_STALE_KEY,
    _FX_CACHE_TTL,
    _FX_STALE_TTL,
    _FX_FALLBACK_RATE,
)

logger = get_logger(__name__)

_cache = RedisCache(settings.REDIS_URL)

_PRICE_CACHE_PREFIX = "price:"
_PRICE_CACHE_TTL_MARKET_OPEN = 300     # 5 min during market hours
_PRICE_CACHE_TTL_MARKET_CLOSED = 86400  # 24 h after market close
_PRICE_CACHE_TTL_HOLDINGS_OPEN = 30    # 30 s during market hours (user-facing)
_PRICE_CACHE_TTL_HOLDINGS_CLOSED = 300  # 5 min outside market hours (user-facing)

# KST market hours constants (reused from prices.py logic)
_KST = timezone(timedelta(hours=9))
_MARKET_OPEN_HOUR_MIN = (9, 0)
_MARKET_CLOSE_HOUR_MIN = (15, 30)


def get_holdings_ttl() -> int:
    """사용자 대면 holdings 전용 캐시 TTL.

    - 장중 (KST 09:00~15:30, 평일): 30초 — SSE와 동기화
    - 그 외: 300초 (5분) — 장외에도 적절히 신선한 값 유지
    """
    now = datetime.now(_KST)
    if now.weekday() >= 5:
        return _PRICE_CACHE_TTL_HOLDINGS_CLOSED
    t = (now.hour, now.minute)
    if _MARKET_OPEN_HOUR_MIN <= t <= _MARKET_CLOSE_HOUR_MIN:
        return _PRICE_CACHE_TTL_HOLDINGS_OPEN
    return _PRICE_CACHE_TTL_HOLDINGS_CLOSED


def get_adaptive_ttl() -> int:
    """현재 시각 기준 적응형 캐시 TTL 반환.

    - 한국 주식 시장 개장 중 (KST 09:00~15:30, 평일): 300초 (5분)
    - 그 외 (장 마감, 주말): 86400초 (24시간)
    """
    now = datetime.now(_KST)
    if now.weekday() >= 5:
        return _PRICE_CACHE_TTL_MARKET_CLOSED
    t = (now.hour, now.minute)
    if _MARKET_OPEN_HOUR_MIN <= t <= _MARKET_CLOSE_HOUR_MIN:
        return _PRICE_CACHE_TTL_MARKET_OPEN
    return _PRICE_CACHE_TTL_MARKET_CLOSED


@dataclass(frozen=True)
class OverseasPriceDetail:
    """해외주식 현재가 상세 정보 (USD 기준)."""

    current: Decimal
    prev_close: Optional[Decimal]
    day_change_rate: Decimal  # % (e.g. 1.25 means +1.25%)
    w52_high: Optional[Decimal] = None
    w52_low: Optional[Decimal] = None


async def _get_headers(app_key: str, app_secret: str) -> dict[str, str]:
    token = await get_kis_access_token(app_key, app_secret)
    return {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "Content-Type": "application/json; charset=utf-8",
    }


async def fetch_domestic_price(
    ticker: str, app_key: str, app_secret: str, client: httpx.AsyncClient
) -> Optional[Decimal]:
    """국내주식 현재가 조회 (FHKST01010100)."""
    headers = await _get_headers(app_key, app_secret)
    headers["tr_id"] = "FHKST01010100"
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": ticker,
    }
    try:
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        data = resp.json()
        price_str: str = data.get("output", {}).get("stck_prpr", "0")
        return Decimal(price_str) if price_str and price_str != "0" else None
    except (httpx.ConnectError, httpx.TimeoutException, OSError, ValueError) as e:
        logger.warning(
            "Failed to fetch domestic price for %s: %s reason=network_unreachable",
            ticker, e,
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to fetch domestic price for %s: %s reason=other",
            ticker, e,
        )
        return None


async def fetch_overseas_price(
    ticker: str, market: str, app_key: str, app_secret: str, client: httpx.AsyncClient
) -> Optional[Decimal]:
    """해외주식 현재가 조회 (HHDFS00000300)."""
    headers = await _get_headers(app_key, app_secret)
    headers["tr_id"] = "HHDFS00000300"
    params = {
        "AUTH": "",
        "EXCD": market,
        "SYMB": ticker,
    }
    try:
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        data = resp.json()
        price_str: str = data.get("output", {}).get("last", "0") or "0"
        if not price_str or price_str == "0":
            return None
        return Decimal(price_str)
    except (httpx.ConnectError, httpx.TimeoutException, OSError, ValueError) as e:
        logger.warning(
            "Failed to fetch overseas price for %s/%s: %s reason=network_unreachable",
            ticker, market, e,
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to fetch overseas price for %s/%s: %s reason=other",
            ticker, market, e,
        )
        return None


async def _cache_price(ticker: str, price: Decimal) -> None:
    """Redis(or in-memory fallback)에 가격을 캐싱."""
    ttl = get_adaptive_ttl()
    await _cache.setex(f"{_PRICE_CACHE_PREFIX}{ticker}", ttl, str(price))


async def _get_cached_price(ticker: str) -> Optional[Decimal]:
    """Redis(or in-memory fallback)에서 캐시된 가격 조회."""
    cached = await _cache.get(f"{_PRICE_CACHE_PREFIX}{ticker}")
    if cached:
        return Decimal(cached)
    return None


async def fetch_domestic_daily_ohlcv(
    ticker: str,
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
    target_date: Optional[str] = None,
) -> Optional[dict]:
    """국내주식 일별 OHLCV 조회 (FHKST01010400).

    Returns dict with open, high, low, close, volume or None on failure.
    target_date: YYYYMMDD format. If None, uses latest available.
    """
    headers = await _get_headers(app_key, app_secret)
    headers["tr_id"] = "FHKST01010400"
    from datetime import date as date_type, timedelta

    end_date = target_date or date_type.today().strftime("%Y%m%d")
    # Request a small window to get today's close
    start_date = (
        date_type.fromisoformat(f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}")
        - timedelta(days=1)
    ).strftime("%Y%m%d")

    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": ticker,
        "fid_input_date_1": start_date,
        "fid_input_date_2": end_date,
        "fid_period_div_code": "D",
        "fid_org_adj_prc": "0",
    }
    try:
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        output_list = resp.json().get("output2", [])
        if not output_list:
            return None
        # Most recent entry first
        row = output_list[0]
        close_str = row.get("stck_clpr", "0")
        if not close_str or close_str == "0":
            return None
        return {
            "open": Decimal(row["stck_oprc"]) if row.get("stck_oprc") else None,
            "high": Decimal(row["stck_hgpr"]) if row.get("stck_hgpr") else None,
            "low": Decimal(row["stck_lwpr"]) if row.get("stck_lwpr") else None,
            "close": Decimal(close_str),
            "volume": int(row["acml_vol"]) if row.get("acml_vol") else None,
        }
    except (httpx.ConnectError, httpx.TimeoutException, OSError, ValueError) as e:
        logger.warning(
            "Failed to fetch daily OHLCV for %s: %s reason=network_unreachable",
            ticker, e,
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to fetch daily OHLCV for %s: %s reason=other",
            ticker, e,
        )
        return None


async def fetch_overseas_daily_ohlcv(
    ticker: str,
    market: str,
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
    target_date: Optional[str] = None,
) -> Optional[dict]:
    """해외주식 일별 OHLCV 조회 (HHDFS76240000).

    Returns dict with open, high, low, close, volume or None on failure.
    target_date: YYYYMMDD format. If None, uses latest available.
    """
    headers = await _get_headers(app_key, app_secret)
    headers["tr_id"] = "HHDFS76240000"

    from datetime import date as date_type

    end_date = target_date or date_type.today().strftime("%Y%m%d")

    params = {
        "AUTH": "",
        "EXCD": market,
        "SYMB": ticker,
        "GUBN": "0",  # 0=일봉
        "BYMD": end_date,
        "MODP": "0",
    }
    try:
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/dailyprice",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        output_list = resp.json().get("output2", [])
        if not output_list:
            return None
        row = output_list[0]
        close_str = row.get("clos", "0")
        if not close_str or close_str == "0":
            return None
        return {
            "open": Decimal(row["open"]) if row.get("open") else None,
            "high": Decimal(row["high"]) if row.get("high") else None,
            "low": Decimal(row["low"]) if row.get("low") else None,
            "close": Decimal(close_str),
            "volume": int(row["tvol"]) if row.get("tvol") else None,
        }
    except (httpx.ConnectError, httpx.TimeoutException, OSError, ValueError) as e:
        logger.warning(
            "Failed to fetch overseas daily OHLCV for %s/%s: %s reason=network_unreachable",
            ticker, market, e,
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to fetch overseas daily OHLCV for %s/%s: %s reason=other",
            ticker, market, e,
        )
        return None


async def fetch_prices_parallel(
    tickers: list[str], app_key: str, app_secret: str, market: str = "domestic"
) -> dict[str, Optional[Decimal]]:
    """여러 종목 현재가를 asyncio.gather로 병렬 조회. 실패 시 Redis 캐시 폴백.

    KIS API 가용성 플래그(get_kis_availability())가 False인 경우
    API 호출을 건너뛰고 캐시 전용 모드로 동작한다.
    """
    price_map: dict[str, Optional[Decimal]] = {}

    if not get_kis_availability():
        logger.warning(
            "[KisPrice] KIS API unavailable — returning cached prices for %d tickers",
            len(tickers),
        )
        for ticker in tickers:
            price_map[ticker] = await _get_cached_price(ticker)
        return price_map

    async with httpx.AsyncClient(timeout=10.0) as client:
        if market == "domestic":
            tasks = [
                fetch_domestic_price(t, app_key, app_secret, client) for t in tickers
            ]
        else:
            tasks = [
                fetch_overseas_price(t, market, app_key, app_secret, client)
                for t in tickers
            ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    total = len(tickers)
    network_failures = sum(
        1
        for r in results
        if isinstance(r, (httpx.ConnectError, httpx.TimeoutException, OSError, ValueError))
        or r is None
    )
    if total > 0 and network_failures / total >= 0.8:
        logger.warning(
            "[KisPrice] KIS bulk fetch failed %d/%d tickers, switching to cache mode",
            network_failures, total,
        )
        set_kis_availability(False, "runtime: bulk connect failure")
        for ticker in tickers:
            price_map[ticker] = await _get_cached_price(ticker)
        return price_map

    for ticker, price in zip(tickers, results):
        if isinstance(price, Exception):
            cached = await _get_cached_price(ticker)
            price_map[ticker] = cached
        elif isinstance(price, Decimal) and price > 0:
            price_map[ticker] = price
            await _cache_price(ticker, price)
        else:
            # KIS API 실패 또는 0 반환 시 캐시에서 폴백
            cached = await _get_cached_price(ticker)
            if cached is not None:
                logger.info("Using cached price for %s: %s", ticker, cached)
            price_map[ticker] = cached

    return price_map



async def fetch_overseas_price_detail(
    ticker: str,
    market: str,
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
) -> Optional[OverseasPriceDetail]:
    """해외주식 현재가 + 전일 대비 + 52주 고/저 조회.

    1차: HHDFS00000300 (현재가, 52주 고/저 포함)
    2차: last == "0" 시 base(전일 종가) fallback
    3차: 52주 고/저 없으면 HHDFS76200200 (price-detail) fallback
    """
    headers = await _get_headers(app_key, app_secret)
    params = {
        "AUTH": "",
        "EXCD": market,
        "SYMB": ticker,
    }
    try:
        async with kis_call_slot():
            resp = await kis_get(
                client,
                f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price",
                headers={**headers, "tr_id": "HHDFS00000300"},
                params=params,
            )
        resp.raise_for_status()
        output = resp.json().get("output", {})

        price_str = output.get("last", "") or ""
        prev_close_str = output.get("base", "") or ""
        # last가 없거나 0이면 전일 종가(base)로 대체
        if not price_str or price_str == "0":
            price_str = prev_close_str
        if not price_str or price_str == "0":
            return None

        rate_str = output.get("rate", "0") or "0"
        w52_high_str = output.get("w52hgpr", "") or ""
        w52_low_str = output.get("w52lwpr", "") or ""

        # 52주 고/저 없으면 HHDFS76200200 fallback
        if not w52_high_str or w52_high_str == "0":
            try:
                async with kis_call_slot():
                    detail_resp = await kis_get(
                        client,
                        f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price-detail",
                        headers={**headers, "tr_id": "HHDFS76200200"},
                        params=params,
                    )
                detail_resp.raise_for_status()
                detail_out = detail_resp.json().get("output", {})
                w52_high_str = (
                    detail_out.get("w52hgpr")
                    or detail_out.get("h52p")
                    or w52_high_str
                )
                w52_low_str = (
                    detail_out.get("w52lwpr")
                    or detail_out.get("l52p")
                    or w52_low_str
                )
            except (httpx.ConnectError, httpx.TimeoutException, OSError, ValueError) as e:
                logger.warning(
                    "52w fallback failed for %s/%s: %s reason=network_unreachable",
                    ticker, market, e,
                )
            except Exception as e:
                logger.warning(
                    "52w fallback failed for %s/%s: %s reason=other",
                    ticker, market, e,
                )

        return OverseasPriceDetail(
            current=Decimal(price_str),
            prev_close=Decimal(prev_close_str) if prev_close_str and prev_close_str != "0" else None,
            day_change_rate=Decimal(rate_str),
            w52_high=Decimal(w52_high_str) if w52_high_str and w52_high_str != "0" else None,
            w52_low=Decimal(w52_low_str) if w52_low_str and w52_low_str != "0" else None,
        )
    except (httpx.ConnectError, httpx.TimeoutException, OSError, ValueError) as e:
        logger.warning(
            "Failed to fetch overseas price detail for %s/%s: %s reason=network_unreachable",
            ticker, market, e,
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to fetch overseas price detail for %s/%s: %s reason=other",
            ticker, market, e,
        )
        return None


async def get_or_fetch_domestic_price(
    ticker: str,
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
    ttl: int | None = None,
) -> Optional[Decimal]:
    """국내주식 현재가 캐시 우선 조회.

    캐시 히트 → KIS API 미호출.
    캐시 미스 → KIS API 조회 후 캐시 저장.
    """
    cached = await _get_cached_price(ticker)
    if cached is not None:
        return cached
    price = await fetch_domestic_price(ticker, app_key, app_secret, client)
    if price is not None and price > 0:
        effective_ttl = ttl if ttl is not None else get_holdings_ttl()
        await _cache.setex(f"{_PRICE_CACHE_PREFIX}{ticker}", effective_ttl, str(price))
    return price


async def fetch_and_cache_domestic_price(
    ticker: str,
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
) -> Optional[Decimal]:
    """국내주식 현재가 KIS 직접 조회 후 Redis 캐시 저장.

    SSE처럼 항상 fresh 가격이 필요하지만 결과를 캐시에 남겨
    이후 holdings 조회가 캐시 히트할 수 있도록 한다.
    """
    price = await fetch_domestic_price(ticker, app_key, app_secret, client)
    if price is not None and price > 0:
        await _cache.setex(
            f"{_PRICE_CACHE_PREFIX}{ticker}", get_holdings_ttl(), str(price)
        )
    return price


async def get_or_fetch_overseas_price(
    ticker: str,
    market: str,
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
    ttl: int | None = None,
) -> Optional[Decimal]:
    """해외주식 현재가 캐시 우선 조회 (current 가격만).

    캐시 히트 → KIS API 미호출.
    캐시 미스 → fetch_overseas_price_detail 호출 후 current 가격만 캐시 저장.
    w52_high/low 등 추가 필드가 필요한 경우 fetch_overseas_price_detail을 직접 사용.
    """
    cached = await _get_cached_price(ticker)
    if cached is not None:
        return cached
    detail = await fetch_overseas_price_detail(ticker, market, app_key, app_secret, client)
    if detail is not None and detail.current > 0:
        effective_ttl = ttl if ttl is not None else get_holdings_ttl()
        await _cache.setex(
            f"{_PRICE_CACHE_PREFIX}{ticker}", effective_ttl, str(detail.current)
        )
        return detail.current
    return None


