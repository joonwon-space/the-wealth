"""배당 API — GET /dividends/upcoming

보유 종목 중 기준일/지급일이 조회 시점 이후인 배당 스케줄을 반환한다.
데이터 소스는 Dividend 테이블 (KIS API 수집 또는 수동 입력). 실제 KIS 배당
조회는 별도 배치/크론으로 테이블을 채우고, 이 API 는 DB 만 읽는다.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.redesign import UpcomingDividend

router = APIRouter(prefix="/dividends", tags=["dividends"])
logger = get_logger(__name__)


@router.get("/upcoming", response_model=list[UpcomingDividend])
@limiter.limit("30/minute")
async def upcoming_dividends(
    request: Request,
    days: int = Query(default=30, ge=1, le=180),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UpcomingDividend]:
    """내 보유 종목의 앞으로 `days` 일 이내 배당 일정을 반환."""
    # 보유 종목 로딩
    portfolios = (
        await db.execute(select(Portfolio.id).where(Portfolio.user_id == current_user.id))
    ).scalars().all()
    if not portfolios:
        return []

    holdings = (
        await db.execute(
            select(Holding).where(Holding.portfolio_id.in_(portfolios))
        )
    ).scalars().all()
    if not holdings:
        return []

    ticker_to_qty: dict[str, Decimal] = {}
    ticker_to_name: dict[str, str] = {}
    for h in holdings:
        ticker_to_qty[h.ticker] = ticker_to_qty.get(h.ticker, Decimal("0")) + h.quantity
        if h.name:
            ticker_to_name[h.ticker] = h.name

    tickers = list(ticker_to_qty.keys())
    today = date.today()
    horizon = today + timedelta(days=days)

    # record_date 또는 payment_date 가 today..horizon 범위 안에 있는 배당.
    # ex_date 기준 정렬 (null 이면 record_date).
    stmt = (
        select(Dividend)
        .where(Dividend.ticker.in_(tickers))
        .where(
            (Dividend.record_date.between(today, horizon))
            | (Dividend.payment_date.between(today, horizon))
        )
        .order_by(
            Dividend.ex_date.asc().nulls_last(),
            Dividend.record_date.asc(),
        )
    )
    dividends = (await db.execute(stmt)).scalars().all()

    result: list[UpcomingDividend] = []
    for d in dividends:
        qty = ticker_to_qty.get(d.ticker)
        estimated = qty * d.amount if qty is not None else None
        result.append(
            UpcomingDividend(
                ticker=d.ticker,
                market=d.market,
                name=ticker_to_name.get(d.ticker),
                quantity=qty,
                ex_date=d.ex_date,
                record_date=d.record_date,
                payment_date=d.payment_date,
                amount=d.amount,
                currency=d.currency,
                kind=d.kind,
                source=d.source,
                estimated_payout=estimated,
            )
        )
    return result
