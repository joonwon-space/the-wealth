"""대시보드 집계 API — 현재가 기반 동적 손익 계산."""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.dashboard import AllocationItem, DashboardSummary, HoldingWithPnL
from app.services.kis_price import fetch_prices_parallel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)

_ZERO = Decimal("0")


def _calc_pnl(quantity: Decimal, avg_price: Decimal, current_price: Optional[Decimal]) -> tuple[Optional[Decimal], Optional[Decimal]]:
    if current_price is None:
        return None, None
    invested = quantity * avg_price
    market_value = quantity * current_price
    pnl_amount = market_value - invested
    pnl_rate = (pnl_amount / invested * 100) if invested else _ZERO
    return pnl_amount, pnl_rate


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    # 사용자 포트폴리오 및 홀딩 조회
    port_result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolios = port_result.scalars().all()

    portfolio_ids = [p.id for p in portfolios]
    if not portfolio_ids:
        return DashboardSummary(
            total_asset=_ZERO,
            total_invested=_ZERO,
            total_pnl_amount=_ZERO,
            total_pnl_rate=_ZERO,
            holdings=[],
            allocation=[],
        )

    hold_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    holdings = hold_result.scalars().all()

    if not holdings:
        return DashboardSummary(
            total_asset=_ZERO,
            total_invested=_ZERO,
            total_pnl_amount=_ZERO,
            total_pnl_rate=_ZERO,
            holdings=[],
            allocation=[],
        )

    # 현재가 병렬 조회 (KIS 자격증명이 없으면 None 반환)
    tickers = list({h.ticker for h in holdings})
    app_key = current_user.kis_app_key_enc or ""
    app_secret = current_user.kis_app_secret_enc or ""

    prices: dict[str, Optional[Decimal]] = {}
    if app_key and app_secret:
        prices = await fetch_prices_parallel(tickers, app_key, app_secret)

    # 수익 계산
    holding_items: list[HoldingWithPnL] = []
    total_asset = _ZERO
    total_invested = _ZERO

    for h in holdings:
        current_price = prices.get(h.ticker)
        pnl_amount, pnl_rate = _calc_pnl(h.quantity, h.avg_price, current_price)
        market_value = h.quantity * current_price if current_price is not None else None

        total_invested += h.quantity * h.avg_price
        total_asset += market_value if market_value is not None else h.quantity * h.avg_price

        holding_items.append(
            HoldingWithPnL(
                id=h.id,
                ticker=h.ticker,
                name=h.name,
                quantity=h.quantity,
                avg_price=h.avg_price,
                current_price=current_price,
                market_value=market_value,
                pnl_amount=pnl_amount,
                pnl_rate=pnl_rate,
            )
        )

    total_pnl_amount = total_asset - total_invested
    total_pnl_rate = (total_pnl_amount / total_invested * 100) if total_invested else _ZERO

    # 자산 배분 계산
    allocation: list[AllocationItem] = []
    if total_asset > _ZERO:
        for item in holding_items:
            value = item.market_value if item.market_value is not None else item.quantity * item.avg_price
            ratio = value / total_asset * 100
            allocation.append(AllocationItem(ticker=item.ticker, name=item.name, value=value, ratio=ratio))

    return DashboardSummary(
        total_asset=total_asset,
        total_invested=total_invested,
        total_pnl_amount=total_pnl_amount,
        total_pnl_rate=total_pnl_rate,
        holdings=holding_items,
        allocation=allocation,
    )
