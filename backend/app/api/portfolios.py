"""Portfolio CRUD endpoints — create, list, update, delete, reorder."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.analytics import invalidate_analytics_cache
from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
    ReorderRequest,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = get_logger(__name__)


def _assert_portfolio_owner(portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    # Single query with LEFT JOIN + GROUP BY instead of N+1
    stmt = (
        select(
            Portfolio,
            KisAccount.label,
            func.count(Holding.id).label("holdings_count"),
            func.coalesce(
                func.sum(Holding.quantity * Holding.avg_price), Decimal("0")
            ).label("total_invested"),
        )
        .outerjoin(KisAccount, KisAccount.id == Portfolio.kis_account_id)
        .outerjoin(Holding, Holding.portfolio_id == Portfolio.id)
        .where(Portfolio.user_id == current_user.id)
        .group_by(Portfolio.id, KisAccount.label)
        .order_by(Portfolio.display_order.asc(), Portfolio.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "name": kis_label if kis_label else p.name,
            "currency": p.currency,
            "display_order": p.display_order,
            "created_at": p.created_at,
            "holdings_count": count,
            "total_invested": invested,
            "kis_account_id": p.kis_account_id,
            "target_value": p.target_value,
        }
        for p, kis_label, count, invested in rows
    ]


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_portfolio(
    request: Request,
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Portfolio:
    max_order_result = await db.execute(
        select(func.max(Portfolio.display_order)).where(Portfolio.user_id == current_user.id)
    )
    max_order = max_order_result.scalar() or -1
    portfolio = Portfolio(
        user_id=current_user.id,
        name=body.name,
        currency=body.currency,
        display_order=max_order + 1,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


@router.patch("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_portfolios(
    body: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """포트폴리오 순서 일괄 업데이트. IDOR 방지: 본인 포트폴리오만 허용."""
    ids = [item.id for item in body.items]
    result = await db.execute(
        select(Portfolio).where(Portfolio.id.in_(ids), Portfolio.user_id == current_user.id)
    )
    owned = {p.id for p in result.scalars().all()}
    if owned != set(ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    for item in body.items:
        await db.execute(
            Portfolio.__table__.update()
            .where(Portfolio.id == item.id)
            .values(display_order=item.display_order)
        )
    await db.commit()


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    body: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    if body.name is not None:
        portfolio.name = body.name
    if body.currency is not None:
        portfolio.currency = body.currency
    if "target_value" in body.model_fields_set:
        portfolio.target_value = body.target_value

    # Sync KIS account label if linked and name changed
    if body.name is not None and portfolio.kis_account_id:
        acct = await db.get(KisAccount, portfolio.kis_account_id)
        if acct:
            acct.label = body.name

    await db.commit()
    await db.refresh(portfolio)
    await invalidate_analytics_cache(current_user.id)

    stats = await db.execute(
        select(
            func.count(Holding.id),
            func.coalesce(func.sum(Holding.quantity * Holding.avg_price), Decimal("0")),
        ).where(Holding.portfolio_id == portfolio.id)
    )
    count, invested = stats.one()
    return {
        "id": portfolio.id,
        "user_id": portfolio.user_id,
        "name": portfolio.name,
        "currency": portfolio.currency,
        "display_order": portfolio.display_order,
        "created_at": portfolio.created_at,
        "holdings_count": count,
        "total_invested": invested,
        "target_value": portfolio.target_value,
    }


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_portfolio(
    request: Request,
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    await db.delete(portfolio)
    await db.commit()
