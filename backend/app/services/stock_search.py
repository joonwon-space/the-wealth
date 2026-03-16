"""종목 검색 — KIS MST/COD 마스터 파일 기반 로컬 검색.

backend/data/mst/ 폴더의 마스터 파일을 파싱하여 Redis에 캐싱 후 검색.
국내: kospi_code.mst, kosdaq_code.mst (고정폭, EUC-KR)
해외: NYSMST.COD, NASMST.COD, AMSMST.COD (탭 구분, EUC-KR)
캐시 TTL: 24시간.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TypedDict

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_KEY = "mst:stock_list"
_CACHE_TTL = 86400  # 24h
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "mst"

_DOMESTIC_FILES = {
    "kospi_code.mst": "KOSPI",
    "kosdaq_code.mst": "KOSDAQ",
}
_OVERSEAS_FILES = {
    "NYSMST.COD": "NYSE",
    "NASMST.COD": "NASDAQ",
    "AMSMST.COD": "AMEX",
}


class StockInfo(TypedDict):
    ticker: str
    name: str
    market: str


def _parse_domestic(filename: str, market: str) -> list[StockInfo]:
    """KOSPI/KOSDAQ MST 파일 파싱 (고정폭, EUC-KR).

    필드: 단축코드(9B) + ISIN(12B) + 한글명(40B) + ...
    """
    filepath = _DATA_DIR / filename
    if not filepath.exists():
        logger.warning("MST file not found: %s", filepath)
        return []

    results: list[StockInfo] = []
    with open(filepath, "rb") as f:
        for line in f:
            if len(line) < 61:
                continue
            short_code = line[0:9].decode("euc-kr", errors="replace").strip()
            name = line[21:61].decode("euc-kr", errors="replace").strip()
            if not short_code or not name:
                continue
            # 6자리 숫자 종목코드만 (펀드코드 F로 시작하는 것 제외)
            if short_code[0].isdigit() and len(short_code) == 6:
                results.append({"ticker": short_code, "name": name, "market": market})
            elif len(short_code) > 6 and short_code[-6:].isdigit():
                # ETF 등 특수코드 (0162Z0 등)
                results.append({"ticker": short_code, "name": name, "market": market})

    logger.info("Parsed %d stocks from %s", len(results), filename)
    return results


def _parse_overseas(filename: str, market: str) -> list[StockInfo]:
    """해외주식 COD 파일 파싱 (탭 구분, EUC-KR).

    필드: 국가 | 거래소코드 | 거래소명 | 거래소한글 | 단축코드 | 코드+거래소 | 한글명 | 영문명 | ...
    """
    filepath = _DATA_DIR / filename
    if not filepath.exists():
        logger.warning("COD file not found: %s", filepath)
        return []

    results: list[StockInfo] = []
    with open(filepath, "rb") as f:
        for line in f:
            decoded = line.decode("euc-kr", errors="replace").strip()
            parts = decoded.split("\t")
            if len(parts) < 8:
                continue
            ticker = parts[4].strip()
            kr_name = parts[6].strip()
            en_name = parts[7].strip()
            if not ticker:
                continue
            # 한글명이 있으면 한글명, 없으면 영문명
            name = kr_name if kr_name else en_name
            results.append({"ticker": ticker, "name": name, "market": market})

    logger.info("Parsed %d stocks from %s", len(results), filename)
    return results


def _load_all_from_files() -> list[StockInfo]:
    """모든 MST/COD 파일에서 종목 로드."""
    stocks: list[StockInfo] = []

    for filename, market in _DOMESTIC_FILES.items():
        try:
            stocks.extend(_parse_domestic(filename, market))
        except Exception as e:
            logger.warning("Failed to parse %s: %s", filename, e)

    for filename, market in _OVERSEAS_FILES.items():
        try:
            stocks.extend(_parse_overseas(filename, market))
        except Exception as e:
            logger.warning("Failed to parse %s: %s", filename, e)

    return stocks


async def _load_stock_list() -> list[StockInfo]:
    """Redis 캐시에서 로드, 없으면 MST 파일에서 파싱 후 캐싱."""
    async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
        cached = await r.get(_CACHE_KEY)
        if cached:
            return json.loads(cached)

        logger.info("Loading stock list from MST/COD files...")
        loop = asyncio.get_event_loop()
        stocks = await loop.run_in_executor(None, _load_all_from_files)

        if stocks:
            await r.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(stocks, ensure_ascii=False))
            logger.info("Cached %d stocks from MST/COD files", len(stocks))
        return stocks


async def search_stocks(query: str, limit: int = 20) -> list[StockInfo]:
    """종목명 또는 티커로 로컬 검색 (대소문자 무시, 정확 매치 우선)."""
    if not query:
        return []
    stocks = await _load_stock_list()
    q = query.strip().upper()

    exact: list[StockInfo] = []
    partial: list[StockInfo] = []

    for s in stocks:
        ticker_upper = s["ticker"].upper()
        name_upper = s["name"].upper()
        if ticker_upper == q or name_upper == q:
            exact.append(s)
        elif q in name_upper or q in ticker_upper:
            partial.append(s)

    return (exact + partial)[:limit]
