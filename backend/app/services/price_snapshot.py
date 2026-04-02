"""일별 종가 스냅샷 저장 및 전일 대비 조회 서비스."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.price_snapshot import PriceSnapshot
from app.services.kis_token import get_kis_access_token

logger = get_logger(__name__)


@dataclass(frozen=True)
class PriceDetail:
    current: Decimal
    prev_close: Decimal
    day_change_rate: Decimal  # % (e.g. 1.25 means +1.25%)
    w52_high: Optional[Decimal]
    w52_low: Optional[Decimal]


async def fetch_domestic_price_detail(
    ticker: str,
    app_key: str,
    app_secret: str,
    client: httpx.AsyncClient,
) -> Optional[PriceDetail]:
    """국내주식 현재가 + 전일 대비 조회 (FHKST01010100).

    Returns PriceDetail with current, prev_close, day_change_rate.
    """
    token = await get_kis_access_token(app_key, app_secret)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST01010100",
        "Content-Type": "application/json; charset=utf-8",
    }
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
        output = resp.json().get("output", {})
        current_str = output.get("stck_prpr", "0")
        prev_close_str = output.get("stck_sdpr", "0")
        change_rate_str = output.get("prdy_ctrt", "0")
        w52_high_str = output.get("w52_hgpr", "")
        w52_low_str = output.get("w52_lwpr", "")
        if not current_str or current_str == "0":
            return None
        return PriceDetail(
            current=Decimal(current_str),
            prev_close=Decimal(prev_close_str),
            day_change_rate=Decimal(change_rate_str),
            w52_high=Decimal(w52_high_str) if w52_high_str else None,
            w52_low=Decimal(w52_low_str) if w52_low_str else None,
        )
    except Exception as e:
        logger.warning("Failed to fetch price detail for %s: %s", ticker, e)
        return None


@dataclass(frozen=True)
class OhlcvData:
    """일별 OHLCV 데이터."""

    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Decimal
    volume: Optional[int]


async def save_snapshots(
    db: AsyncSession,
    ticker_prices: dict[str, Decimal],
    snapshot_date: Optional[date] = None,
) -> int:
    """종목별 종가를 price_snapshots 테이블에 upsert. 저장 건수 반환."""
    if not ticker_prices:
        return 0

    today = snapshot_date or datetime.now(timezone.utc).date()
    rows = [
        {"ticker": ticker, "snapshot_date": today, "close": float(price)}
        for ticker, price in ticker_prices.items()
    ]

    stmt = (
        insert(PriceSnapshot)
        .values(rows)
        .on_conflict_do_update(
            constraint="uq_price_snapshot_ticker_date",
            set_={"close": insert(PriceSnapshot).excluded.close},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return len(rows)


async def save_ohlcv_snapshots(
    db: AsyncSession,
    ticker_ohlcv: dict[str, OhlcvData],
    snapshot_date: Optional[date] = None,
) -> int:
    """종목별 OHLCV를 price_snapshots 테이블에 upsert. 저장 건수 반환."""
    if not ticker_ohlcv:
        return 0

    today = snapshot_date or datetime.now(timezone.utc).date()
    rows = [
        {
            "ticker": ticker,
            "snapshot_date": today,
            "open": float(data.open) if data.open is not None else None,
            "high": float(data.high) if data.high is not None else None,
            "low": float(data.low) if data.low is not None else None,
            "close": float(data.close),
            "volume": data.volume,
        }
        for ticker, data in ticker_ohlcv.items()
    ]

    stmt = (
        insert(PriceSnapshot)
        .values(rows)
        .on_conflict_do_update(
            constraint="uq_price_snapshot_ticker_date",
            set_={
                "open": insert(PriceSnapshot).excluded.open,
                "high": insert(PriceSnapshot).excluded.high,
                "low": insert(PriceSnapshot).excluded.low,
                "close": insert(PriceSnapshot).excluded.close,
                "volume": insert(PriceSnapshot).excluded.volume,
            },
        )
    )
    await db.execute(stmt)
    await db.commit()
    return len(rows)


async def get_prev_close(
    db: AsyncSession,
    tickers: list[str],
    ref_date: Optional[date] = None,
) -> dict[str, Decimal]:
    """가장 최근 price_snapshots 레코드에서 전일 종가 조회."""
    if not tickers:
        return {}

    today = ref_date or datetime.now(timezone.utc).date()

    # DISTINCT ON (ticker) returns only the latest snapshot per ticker —
    # PostgreSQL reads ~N rows (one per ticker) instead of the full history.
    result = await db.execute(
        text(
            """
            SELECT DISTINCT ON (ticker) ticker, close
            FROM price_snapshots
            WHERE ticker = ANY(:tickers)
              AND snapshot_date < :today
            ORDER BY ticker, snapshot_date DESC
            """
        ),
        {"tickers": list(tickers), "today": today},
    )
    rows = result.fetchall()

    return {row.ticker: Decimal(str(row.close)) for row in rows}
