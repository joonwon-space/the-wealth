"""KIS 현재가 조회 서비스 (국내 + 해외주식, asyncio.gather 병렬 처리).

Redis에 마지막 조회 가격을 캐싱(TTL 1h)하여 KIS API 장애 시 폴백.
"""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Optional

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.services.kis_token import get_kis_access_token

logger = logging.getLogger(__name__)

_PRICE_CACHE_PREFIX = "price:"
_PRICE_CACHE_TTL = 3600  # 1h


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
        resp = await client.get(
            f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        price_str: str = data.get("output", {}).get("stck_prpr", "0")
        return Decimal(price_str) if price_str else None
    except Exception as e:
        logger.warning("Failed to fetch domestic price for %s: %s", ticker, e)
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
        resp = await client.get(
            f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        price_str: str = data.get("output", {}).get("last", "0")
        return Decimal(price_str) if price_str else None
    except Exception as e:
        logger.warning("Failed to fetch overseas price for %s/%s: %s", ticker, market, e)
        return None


async def _cache_price(ticker: str, price: Decimal) -> None:
    """Redis에 가격을 캐싱."""
    try:
        async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
            await r.setex(f"{_PRICE_CACHE_PREFIX}{ticker}", _PRICE_CACHE_TTL, str(price))
    except Exception as e:
        logger.debug("Failed to cache price for %s: %s", ticker, e)


async def _get_cached_price(ticker: str) -> Optional[Decimal]:
    """Redis에서 캐시된 가격 조회."""
    try:
        async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
            cached = await r.get(f"{_PRICE_CACHE_PREFIX}{ticker}")
            if cached:
                return Decimal(cached)
    except Exception as e:
        logger.debug("Failed to get cached price for %s: %s", ticker, e)
    return None


async def fetch_prices_parallel(
    tickers: list[str], app_key: str, app_secret: str, market: str = "domestic"
) -> dict[str, Optional[Decimal]]:
    """여러 종목 현재가를 asyncio.gather로 병렬 조회. 실패 시 Redis 캐시 폴백."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        if market == "domestic":
            tasks = [fetch_domestic_price(t, app_key, app_secret, client) for t in tickers]
        else:
            tasks = [fetch_overseas_price(t, market, app_key, app_secret, client) for t in tickers]
        results = await asyncio.gather(*tasks)

    price_map: dict[str, Optional[Decimal]] = {}
    for ticker, price in zip(tickers, results):
        if price is not None:
            price_map[ticker] = price
            await _cache_price(ticker, price)
        else:
            # KIS API 실패 시 캐시에서 폴백
            cached = await _get_cached_price(ticker)
            if cached is not None:
                logger.info("Using cached price for %s: %s", ticker, cached)
            price_map[ticker] = cached

    return price_map
