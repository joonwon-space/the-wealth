"""가격 히스토리 및 SSE 실시간 가격 API."""

import asyncio
import json
import logging
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt
from app.db.session import AsyncSessionLocal, get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.services.kis_price import fetch_domestic_price

router = APIRouter(prefix="/prices", tags=["prices"])
logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))
_MARKET_OPEN = (9, 0)    # KST 09:00
_MARKET_CLOSE = (15, 30)  # KST 15:30
_SSE_INTERVAL = 30        # seconds
_SSE_TIMEOUT = 3600       # 1 hour max connection


def _is_market_open() -> bool:
    now = datetime.now(_KST)
    if now.weekday() >= 5:
        return False
    t = (now.hour, now.minute)
    return _MARKET_OPEN <= t <= _MARKET_CLOSE


@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    limit: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """종목 일별 종가 히스토리 조회.

    - `from`: 시작일 (inclusive), 기본값 없음
    - `to`: 종료일 (inclusive), 기본값 없음
    - `limit`: 최대 반환 건수 (기본 90일, 최대 365일)
    """
    stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker == ticker.upper())
        .order_by(PriceSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    if from_date:
        stmt = stmt.where(PriceSnapshot.snapshot_date >= from_date)
    if to_date:
        stmt = stmt.where(PriceSnapshot.snapshot_date <= to_date)

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        {
            "date": snap.snapshot_date.isoformat(),
            "close": str(Decimal(str(snap.close))),
        }
        for snap in sorted(snapshots, key=lambda s: s.snapshot_date)
    ]


@router.get("/stream")
async def stream_prices(
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """보유 종목 현재가 SSE 스트림.

    30초 간격으로 가격을 push한다. 시장 미개장 시 상태만 전송.
    최대 연결 시간 1시간.
    """

    async def event_generator():
        elapsed = 0
        async with AsyncSessionLocal() as db:
            # 보유 종목 + KIS 계정 조회
            port_result = await db.execute(
                select(Portfolio).where(Portfolio.user_id == current_user.id)
            )
            portfolio_ids = [p.id for p in port_result.scalars().all()]

            acct_result = await db.execute(
                select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
            )
            acct = acct_result.scalar_one_or_none()

        if not portfolio_ids or not acct:
            yield "data: {\"error\": \"no_data\"}\n\n"
            return

        app_key = decrypt(acct.app_key_enc)
        app_secret = decrypt(acct.app_secret_enc)

        while elapsed < _SSE_TIMEOUT:
            if not _is_market_open():
                yield f"data: {json.dumps({'market_open': False})}\n\n"
                await asyncio.sleep(_SSE_INTERVAL)
                elapsed += _SSE_INTERVAL
                continue

            try:
                async with AsyncSessionLocal() as db:
                    hold_result = await db.execute(
                        select(Holding.ticker).distinct().where(
                            Holding.portfolio_id.in_(portfolio_ids)
                        )
                    )
                    tickers = [r[0] for r in hold_result.all()]

                if not tickers:
                    yield f"data: {json.dumps({'prices': {}})}\n\n"
                else:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        results = await asyncio.gather(
                            *[fetch_domestic_price(t, app_key, app_secret, client) for t in tickers],
                            return_exceptions=True,
                        )
                    prices = {
                        ticker: str(price)
                        for ticker, price in zip(tickers, results)
                        if isinstance(price, Decimal) and price > 0
                    }
                    yield f"data: {json.dumps({'market_open': True, 'prices': prices})}\n\n"
            except Exception as e:
                logger.warning("SSE price fetch error: %s", e)
                yield f"data: {json.dumps({'error': 'fetch_failed'})}\n\n"

            await asyncio.sleep(_SSE_INTERVAL)
            elapsed += _SSE_INTERVAL

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
