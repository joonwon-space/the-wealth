"""KRX 상장 종목 로컬 검색.

KIS OpenAPI에는 종목명 검색 API가 없으므로,
KRX KIND에서 KOSPI + KOSDAQ 상장 종목 리스트를 받아 Redis에 캐싱 후 로컬 검색.
ETF는 Naver Finance API에서 가져와 합산 캐싱.
캐시 TTL: 24시간 (매일 갱신).
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import TypedDict

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_KEY = "krx:stock_list"
_CACHE_TTL = 86400  # 24h
_MARKETS = {"stockMkt": "KOSPI", "kosdaqMkt": "KOSDAQ"}
_KRX_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&marketType={market}"
_NAVER_ETF_URL = "https://finance.naver.com/api/sise/etfItemList.nhn"


class StockInfo(TypedDict):
    ticker: str
    name: str
    market: str


def _fetch_krx(market: str) -> list[StockInfo]:
    url = _KRX_URL.format(market=market)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode("euc-kr", errors="ignore")

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", raw, re.DOTALL)
    results: list[StockInfo] = []
    for row in rows[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) < 2:
            continue
        name = re.sub("<[^>]+>", "", cells[0]).strip()
        ticker = next(
            (re.sub("<[^>]+>", "", c).strip() for c in cells if re.sub("<[^>]+>", "", c).strip().isdigit() and len(re.sub("<[^>]+>", "", c).strip()) == 6),
            None,
        )
        if name and ticker:
            results.append({"ticker": ticker, "name": name, "market": _MARKETS[market]})
    return results


def _fetch_naver_etf() -> list[StockInfo]:
    """Naver Finance API에서 국내 상장 ETF 목록 조회."""
    params = "etfType=0&targetColumn=market_sum&sortOrder=desc&page=1&pageSize=9999"
    url = f"{_NAVER_ETF_URL}?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.naver.com/etf/",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()

    data = json.loads(raw.decode("euc-kr", errors="ignore"))
    items = data.get("result", {}).get("etfItemList", [])
    return [
        {"ticker": item["itemcode"], "name": item["itemname"], "market": "ETF"}
        for item in items
        if item.get("itemcode") and item.get("itemname")
    ]


async def _load_stock_list() -> list[StockInfo]:
    """Redis에서 캐시 로드, 없으면 KRX에서 fetch 후 캐싱."""
    async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as redis:
        cached = await redis.get(_CACHE_KEY)
        if cached:
            return json.loads(cached)

        logger.info("Fetching KRX stock list + Naver ETF list...")
        stocks: list[StockInfo] = []
        for market in _MARKETS:
            try:
                stocks.extend(_fetch_krx(market))
            except Exception as e:
                logger.warning("Failed to fetch KRX %s: %s", market, e)

        try:
            etfs = _fetch_naver_etf()
            stocks.extend(etfs)
            logger.info("Fetched %d ETFs from Naver Finance", len(etfs))
        except Exception as e:
            logger.warning("Failed to fetch Naver ETF list: %s", e)

        if stocks:
            await redis.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(stocks, ensure_ascii=False))
            logger.info("Cached %d items (stocks + ETFs)", len(stocks))
        return stocks


async def search_stocks(query: str, limit: int = 20) -> list[StockInfo]:
    """종목명 또는 티커로 로컬 검색 (대소문자 무시)."""
    if not query:
        return []
    stocks = await _load_stock_list()
    q = query.strip().upper()
    matched = [
        s for s in stocks
        if q in s["name"].upper() or q in s["ticker"]
    ]
    return matched[:limit]
