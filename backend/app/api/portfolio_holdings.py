"""Portfolio holdings endpoints — list, add, bulk-add, edit, delete, with-prices."""

import asyncio
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.analytics import invalidate_analytics_cache
from app.api.deps import get_current_user
from app.api.prices import invalidate_sse_ticker_cache
from app.core.encryption import decrypt
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.ticker import is_domestic
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    BulkHoldingRequest,
    BulkHoldingResult,
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
)
from app.services.kis_price import (
    fetch_usd_krw_rate,
    get_or_fetch_domestic_price,
    get_or_fetch_overseas_price,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = get_logger(__name__)

_MARKET_MAP = {
    "NASD": "NAS", "NYSE": "NYS", "AMEX": "AMS",
    "SEHK": "HKS", "TKSE": "TSE", "SHAA": "SHS",
    "SZAA": "SZS", "HASE": "HNX", "VNSE": "HSX",
}


def _assert_portfolio_owner(portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


def _assert_holding_owner(holding: Holding, portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id or holding.portfolio_id != portfolio.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
@limiter.limit("30/minute")
async def list_holdings(
    request: Request,
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Holding]:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    return list(result.scalars().all())


@router.get("/{portfolio_id}/holdings/with-prices")
@limiter.limit("30/minute")
async def list_holdings_with_prices(
    request: Request,
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Holdings with current prices and P&L from the linked KIS account."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    holdings = list(result.scalars().all())
    if not holdings:
        return []

    overseas_holdings = [h for h in holdings if not is_domestic(h.ticker)]
    ticker_to_market = {
        h.ticker: _MARKET_MAP.get(h.market or "", h.market or "NAS")
        for h in overseas_holdings
    }

    prices: dict[str, Decimal | None] = {}
    exchange_rate = Decimal("1450")

    acct: KisAccount | None = None
    if portfolio.kis_account_id:
        acct = await db.get(KisAccount, portfolio.kis_account_id)
    if acct is None:
        # Fallback: use any KIS account from the same user for price lookups
        fallback_result = await db.execute(
            select(KisAccount)
            .where(KisAccount.user_id == current_user.id)
            .limit(1)
        )
        acct = fallback_result.scalar_one_or_none()
    if acct:
        try:
            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)
            domestic_tickers = list({h.ticker for h in holdings if is_domestic(h.ticker)})
            overseas_tickers = list({h.ticker for h in overseas_holdings})
            async with httpx.AsyncClient(timeout=10.0) as client:
                domestic_tasks = [
                    get_or_fetch_domestic_price(t, app_key, app_secret, client)
                    for t in domestic_tickers
                ]
                overseas_tasks = [
                    get_or_fetch_overseas_price(t, ticker_to_market[t], app_key, app_secret, client)
                    for t in overseas_tickers
                ]
                fx_task = (
                    fetch_usd_krw_rate(app_key, app_secret, client)
                    if overseas_holdings
                    else asyncio.sleep(0, result=Decimal("1450"))
                )
                *all_prices, fx = await asyncio.gather(
                    *domestic_tasks, *overseas_tasks, fx_task, return_exceptions=True
                )

            domestic_results = all_prices[: len(domestic_tickers)]
            overseas_results = all_prices[len(domestic_tickers):]

            for ticker, price in zip(domestic_tickers, domestic_results):
                if isinstance(price, Decimal) and price > 0:
                    prices[ticker] = price
            if isinstance(fx, Decimal):
                exchange_rate = fx
            for ticker, price in zip(overseas_tickers, overseas_results):
                if isinstance(price, Decimal) and price > 0:
                    prices[ticker] = price

        except Exception as e:
            logger.warning(
                "Failed to fetch prices for portfolio %d: %s", portfolio_id, e
            )

    items = []
    for h in holdings:
        is_overseas = not is_domestic(h.ticker)
        cp = prices.get(h.ticker)
        invested = h.quantity * h.avg_price

        if is_overseas:
            invested_krw = invested * exchange_rate
            mv_usd = h.quantity * cp if cp is not None else None
            mv_krw = mv_usd * exchange_rate if mv_usd is not None else None
            pnl_krw = (mv_krw - invested_krw) if mv_krw is not None and invested_krw else None
            pnl_rate = (
                (pnl_krw / invested_krw * 100)
                if pnl_krw is not None and invested_krw
                else None
            )
            items.append({
                "id": h.id,
                "ticker": h.ticker,
                "name": h.name,
                "quantity": str(h.quantity),
                "avg_price": str(h.avg_price),
                "current_price": str(cp) if cp is not None else None,
                "market_value": str(mv_usd) if mv_usd is not None else None,
                "market_value_krw": str(mv_krw) if mv_krw is not None else None,
                "pnl_amount": str(pnl_krw) if pnl_krw is not None else None,
                "pnl_rate": str(pnl_rate) if pnl_rate is not None else None,
                "exchange_rate": str(exchange_rate),
                "currency": "USD",
            })
        else:
            mv = h.quantity * cp if cp is not None else None
            pnl = (mv - invested) if mv is not None and invested else None
            pnl_rate = (pnl / invested * 100) if pnl is not None and invested else None
            items.append({
                "id": h.id,
                "ticker": h.ticker,
                "name": h.name,
                "quantity": str(h.quantity),
                "avg_price": str(h.avg_price),
                "current_price": str(cp) if cp is not None else None,
                "market_value": str(mv) if mv is not None else None,
                "market_value_krw": str(mv) if mv is not None else None,
                "pnl_amount": str(pnl) if pnl is not None else None,
                "pnl_rate": str(pnl_rate) if pnl_rate is not None else None,
                "exchange_rate": None,
                "currency": "KRW",
            })
    return items


@router.post(
    "/{portfolio_id}/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def add_holding(
    request: Request,
    portfolio_id: int,
    body: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Holding:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    holding = Holding(
        portfolio_id=portfolio_id,
        ticker=body.ticker,
        name=body.name,
        quantity=body.quantity,
        avg_price=body.avg_price,
        market=body.market,
    )
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    await invalidate_analytics_cache(current_user.id)
    await invalidate_sse_ticker_cache(current_user.id)
    return holding


@router.post(
    "/{portfolio_id}/holdings/bulk",
    response_model=BulkHoldingResult,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("60/minute")
async def bulk_add_holdings(
    request: Request,
    portfolio_id: int,
    body: BulkHoldingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BulkHoldingResult:
    """보유 종목 일괄 등록/업데이트.

    - 신규 ticker: 새 Holding 생성
    - 기존 ticker: 수량 합산 + 가중평균 평단가 업데이트
    - 최대 100건; 유효성 오류 항목은 건너뛰고 errors 목록에 추가
    """
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    existing_result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    existing_map: dict[str, Holding] = {h.ticker: h for h in existing_result.scalars().all()}

    created = 0
    updated = 0
    errors: list[str] = []

    for item in body.items:
        try:
            if item.ticker in existing_map:
                existing = existing_map[item.ticker]
                old_qty = existing.quantity
                old_price = existing.avg_price
                new_qty = item.quantity
                new_price = item.avg_price
                total_qty = old_qty + new_qty
                weighted_avg = (old_qty * old_price + new_qty * new_price) / total_qty
                existing.quantity = total_qty
                existing.avg_price = weighted_avg
                updated += 1
            else:
                holding = Holding(
                    portfolio_id=portfolio_id,
                    ticker=item.ticker,
                    name=item.name,
                    quantity=item.quantity,
                    avg_price=item.avg_price,
                    market=item.market,
                )
                db.add(holding)
                existing_map[item.ticker] = holding
                created += 1
        except Exception as exc:
            errors.append(f"{item.ticker}: {exc}")

    await db.commit()
    await invalidate_analytics_cache(current_user.id)
    await invalidate_sse_ticker_cache(current_user.id)
    logger.info(
        "Bulk holdings upsert: portfolio=%d created=%d updated=%d errors=%d",
        portfolio_id, created, updated, len(errors),
    )
    return BulkHoldingResult(created=created, updated=updated, errors=errors)


@router.patch("/holdings/{holding_id}", response_model=HoldingResponse)
@limiter.limit("60/minute")
async def update_holding(
    request: Request,
    holding_id: int,
    body: HoldingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Holding:
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found"
        )
    portfolio = await db.get(Portfolio, holding.portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_holding_owner(holding, portfolio, current_user)

    if body.quantity is not None:
        holding.quantity = body.quantity
    if body.avg_price is not None:
        holding.avg_price = body.avg_price
    await db.commit()
    await db.refresh(holding)
    await invalidate_analytics_cache(current_user.id)
    return holding


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_holding(
    request: Request,
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found"
        )
    portfolio = await db.get(Portfolio, holding.portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_holding_owner(holding, portfolio, current_user)

    await db.delete(holding)
    await db.commit()
    await invalidate_analytics_cache(current_user.id)
    await invalidate_sse_ticker_cache(current_user.id)
