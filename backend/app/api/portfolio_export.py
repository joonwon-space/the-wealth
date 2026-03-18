"""포트폴리오 CSV 내보내기 API."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User

router = APIRouter(prefix="/portfolios", tags=["portfolio-export"])
logger = get_logger(__name__)


def _assert_portfolio_owner(portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


@router.get("/{portfolio_id}/export/csv")
async def export_holdings_csv(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """보유 종목 CSV 내보내기."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Holding)
        .where(Holding.portfolio_id == portfolio_id)
        .order_by(Holding.ticker)
    )
    holdings = list(result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ticker", "name", "quantity", "avg_price", "invested", "created_at"])
    for h in holdings:
        invested = h.quantity * h.avg_price
        writer.writerow([
            h.ticker,
            h.name,
            str(h.quantity),
            str(h.avg_price),
            str(invested),
            h.created_at.isoformat(),
        ])

    output.seek(0)
    filename = f"holdings_portfolio_{portfolio_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{portfolio_id}/transactions/export/csv")
async def export_transactions_csv(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """거래 내역 CSV 내보내기."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.traded_at.desc())
    )
    transactions = list(result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "ticker", "type", "quantity", "price", "total", "traded_at"])
    for txn in transactions:
        total = txn.quantity * txn.price
        writer.writerow([
            txn.id,
            txn.ticker,
            txn.type,
            str(txn.quantity),
            str(txn.price),
            str(total),
            txn.traded_at.isoformat(),
        ])

    output.seek(0)
    filename = f"transactions_portfolio_{portfolio_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
