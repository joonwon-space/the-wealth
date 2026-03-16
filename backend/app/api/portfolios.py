from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
    PortfolioCreate,
    PortfolioResponse,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def _assert_portfolio_owner(portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def _assert_holding_owner(holding: Holding, portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id or holding.portfolio_id != portfolio.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolios = list(result.scalars().all())

    response = []
    for p in portfolios:
        stats = await db.execute(
            select(
                func.count(Holding.id),
                func.coalesce(func.sum(Holding.quantity * Holding.avg_price), Decimal("0")),
            ).where(Holding.portfolio_id == p.id)
        )
        count, invested = stats.one()
        response.append({
            "id": p.id,
            "user_id": p.user_id,
            "name": p.name,
            "currency": p.currency,
            "created_at": p.created_at,
            "holdings_count": count,
            "total_invested": invested,
        })
    return response


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Portfolio:
    portfolio = Portfolio(user_id=current_user.id, name=body.name, currency=body.currency)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    _assert_portfolio_owner(portfolio, current_user)
    await db.delete(portfolio)
    await db.commit()


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Holding]:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(select(Holding).where(Holding.portfolio_id == portfolio_id))
    return list(result.scalars().all())


@router.post("/{portfolio_id}/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def add_holding(
    portfolio_id: int,
    body: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Holding:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    _assert_portfolio_owner(portfolio, current_user)

    holding = Holding(
        portfolio_id=portfolio_id,
        ticker=body.ticker,
        name=body.name,
        quantity=body.quantity,
        avg_price=body.avg_price,
    )
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    return holding


@router.patch("/holdings/{holding_id}", response_model=HoldingResponse)
async def update_holding(
    holding_id: int,
    body: HoldingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Holding:
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    portfolio = await db.get(Portfolio, holding.portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    _assert_holding_owner(holding, portfolio, current_user)

    if body.quantity is not None:
        holding.quantity = body.quantity
    if body.avg_price is not None:
        holding.avg_price = body.avg_price
    await db.commit()
    await db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    holding = await db.get(Holding, holding_id)
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    portfolio = await db.get(Portfolio, holding.portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    _assert_holding_owner(holding, portfolio, current_user)

    await db.delete(holding)
    await db.commit()
