"""KIS 현재가 조회 서비스 (국내 + 해외주식, asyncio.gather 병렬 처리)."""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.services.kis_token import get_kis_access_token

logger = logging.getLogger(__name__)


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


async def fetch_prices_parallel(
    tickers: list[str], app_key: str, app_secret: str, market: str = "domestic"
) -> dict[str, Optional[Decimal]]:
    """여러 종목 현재가를 asyncio.gather로 병렬 조회."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        if market == "domestic":
            tasks = [fetch_domestic_price(t, app_key, app_secret, client) for t in tickers]
        else:
            tasks = [fetch_overseas_price(t, market, app_key, app_secret, client) for t in tickers]
        results = await asyncio.gather(*tasks)
    return dict(zip(tickers, results))
