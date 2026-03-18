from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User
from app.core.logging import get_logger
from app.services.kis_price import fetch_prices_parallel
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
    PortfolioCreate,
    PortfolioResponse,
    TransactionCreate,
    TransactionResponse,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = get_logger(__name__)


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
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "name": kis_label if kis_label else p.name,
            "currency": p.currency,
            "created_at": p.created_at,
            "holdings_count": count,
            "total_invested": invested,
        }
        for p, kis_label, count, invested in rows
    ]


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Portfolio:
    portfolio = Portfolio(
        user_id=current_user.id, name=body.name, currency=body.currency
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    portfolio.name = body.name
    if body.currency:
        portfolio.currency = body.currency

    # Sync KIS account label if linked
    if portfolio.kis_account_id:
        acct = await db.get(KisAccount, portfolio.kis_account_id)
        if acct:
            acct.label = body.name

    await db.commit()
    await db.refresh(portfolio)

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
        "created_at": portfolio.created_at,
        "holdings_count": count,
        "total_invested": invested,
    }


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
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


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
async def list_holdings(
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
async def list_holdings_with_prices(
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

    # Fetch prices via linked KIS account
    prices: dict[str, Decimal | None] = {}
    if portfolio.kis_account_id:
        acct = await db.get(KisAccount, portfolio.kis_account_id)
        if acct:
            try:
                app_key = decrypt(acct.app_key_enc)
                app_secret = decrypt(acct.app_secret_enc)
                tickers = list({h.ticker for h in holdings})
                prices = await fetch_prices_parallel(tickers, app_key, app_secret)
            except Exception as e:
                logger.warning(
                    "Failed to fetch prices for portfolio %d: %s", portfolio_id, e
                )

    items = []
    for h in holdings:
        cp = prices.get(h.ticker)
        invested = h.quantity * h.avg_price
        mv = h.quantity * cp if cp is not None else None
        pnl = mv - invested if mv is not None else None
        pnl_rate = (pnl / invested * 100) if pnl is not None and invested else None
        items.append(
            {
                "id": h.id,
                "ticker": h.ticker,
                "name": h.name,
                "quantity": str(h.quantity),
                "avg_price": str(h.avg_price),
                "current_price": str(cp) if cp is not None else None,
                "market_value": str(mv) if mv is not None else None,
                "pnl_amount": str(pnl) if pnl is not None else None,
                "pnl_rate": str(pnl_rate) if pnl_rate is not None else None,
            }
        )
    return items


@router.post(
    "/{portfolio_id}/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_holding(
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
    return holding


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
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


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    portfolio_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Transaction]:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.traded_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    portfolio_id: int,
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    txn = Transaction(
        portfolio_id=portfolio_id,
        ticker=body.ticker,
        type=body.type,
        quantity=body.quantity,
        price=body.price,
    )
    if body.traded_at:
        txn.traded_at = body.traded_at
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    txn = await db.get(Transaction, transaction_id)
    if not txn or txn.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    portfolio = await db.get(Portfolio, txn.portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    # Soft delete: set deleted_at instead of hard delete
    txn.deleted_at = datetime.now(timezone.utc)
    await db.commit()


