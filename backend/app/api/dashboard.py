"""대시보드 집계 API — 현재가 기반 동적 손익 계산."""

import asyncio
import logging
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.dashboard import AllocationItem, DashboardSummary, HoldingWithPnL
from app.services.kis_price import fetch_prices_parallel
from app.services.price_snapshot import fetch_domestic_price_detail

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)

_ZERO = Decimal("0")


def _calc_pnl(
    quantity: Decimal, avg_price: Decimal, current_price: Optional[Decimal]
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    if current_price is None:
        return None, None
    invested = quantity * avg_price
    market_value = quantity * current_price
    pnl_amount = market_value - invested
    pnl_rate = (pnl_amount / invested * 100) if invested else None
    return pnl_amount, pnl_rate


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    # 사용자 포트폴리오 및 홀딩 조회
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
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
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids)).limit(500)
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

    # Fetch prices using first available KIS account credentials
    tickers = list({h.ticker for h in holdings})
    prices: dict[str, Optional[Decimal]] = {}

    # Force-refresh: clear price cache for these tickers
    if refresh and tickers:
        try:
            async with aioredis.from_url(settings.REDIS_URL) as r:
                keys = [f"price:{t}" for t in tickers]
                await r.delete(*keys)
        except Exception:
            pass

    acct_result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
    )
    kis_acct = acct_result.scalar_one_or_none()

    day_change_rates: dict[str, Optional[Decimal]] = {}

    if kis_acct:
        try:
            app_key = decrypt(kis_acct.app_key_enc)
            app_secret = decrypt(kis_acct.app_secret_enc)
            prices = await fetch_prices_parallel(tickers, app_key, app_secret)

            # 전일 대비율 병렬 조회
            async with httpx.AsyncClient(timeout=10.0) as client:
                details = await asyncio.gather(
                    *[fetch_domestic_price_detail(t, app_key, app_secret, client) for t in tickers],
                    return_exceptions=True,
                )
            for ticker, detail in zip(tickers, details):
                if detail and not isinstance(detail, Exception):
                    day_change_rates[ticker] = detail.day_change_rate
        except Exception as e:
            logger.warning("Failed to fetch prices: %s", e)

    # 수익 계산
    holding_items: list[HoldingWithPnL] = []
    total_asset = _ZERO
    total_invested = _ZERO

    for h in holdings:
        current_price = prices.get(h.ticker)
        pnl_amount, pnl_rate = _calc_pnl(h.quantity, h.avg_price, current_price)
        market_value = h.quantity * current_price if current_price is not None else None

        total_invested += h.quantity * h.avg_price
        total_asset += (
            market_value if market_value is not None else h.quantity * h.avg_price
        )

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
                day_change_rate=day_change_rates.get(h.ticker),
            )
        )

    total_pnl_amount = total_asset - total_invested
    total_pnl_rate = (
        (total_pnl_amount / total_invested * 100) if total_invested else _ZERO
    )

    # 자산 배분 계산
    allocation: list[AllocationItem] = []
    if total_asset > _ZERO:
        for item in holding_items:
            value = (
                item.market_value
                if item.market_value is not None
                else item.quantity * item.avg_price
            )
            ratio = value / total_asset * 100
            allocation.append(
                AllocationItem(
                    ticker=item.ticker, name=item.name, value=value, ratio=ratio
                )
            )

    # 포트폴리오 전일 대비: 시가총액 가중 평균
    total_day_change_rate: Optional[Decimal] = None
    weighted_sum = _ZERO
    weight_total = _ZERO
    for item in holding_items:
        if item.day_change_rate is not None and item.market_value is not None:
            weighted_sum += item.day_change_rate * item.market_value
            weight_total += item.market_value
    if weight_total > _ZERO:
        total_day_change_rate = weighted_sum / weight_total

    return DashboardSummary(
        total_asset=total_asset,
        total_invested=total_invested,
        total_pnl_amount=total_pnl_amount,
        total_pnl_rate=total_pnl_rate,
        total_day_change_rate=total_day_change_rate,
        holdings=holding_items,
        allocation=allocation,
    )
