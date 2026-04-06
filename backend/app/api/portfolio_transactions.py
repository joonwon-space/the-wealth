"""Portfolio transaction endpoints — list, paginated-list, create, delete, update-memo, KIS-transactions."""

import asyncio
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.portfolio import (
    TransactionCreate,
    TransactionMemoUpdate,
    TransactionPage,
    TransactionResponse,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = get_logger(__name__)


def _assert_portfolio_owner(portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


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


@router.get("/{portfolio_id}/transactions/paginated", response_model=TransactionPage)
async def list_transactions_paginated(
    portfolio_id: int,
    cursor: int = Query(default=0, ge=0, description="마지막으로 조회한 transaction ID (0이면 처음부터)"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """커서 기반 트랜잭션 페이지네이션.

    cursor: 이전 페이지의 마지막 트랜잭션 ID (0이면 첫 페이지).
    Returns: { items, next_cursor, has_more }
    """
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    query = (
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.traded_at.desc(), Transaction.id.desc())
    )
    if cursor > 0:
        ref_txn = await db.get(Transaction, cursor)
        if ref_txn and ref_txn.portfolio_id == portfolio_id:
            query = query.where(
                (Transaction.traded_at < ref_txn.traded_at)
                | (
                    (Transaction.traded_at == ref_txn.traded_at)
                    & (Transaction.id < cursor)
                )
            )

    result = await db.execute(query.limit(limit + 1))
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = items[-1].id if has_more else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


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
    txn.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.patch(
    "/{portfolio_id}/transactions/{transaction_id}",
    response_model=TransactionResponse,
)
async def update_transaction_memo(
    portfolio_id: int,
    transaction_id: int,
    body: TransactionMemoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    """거래 메모 업데이트 (인라인 편집)."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)

    txn = await db.get(Transaction, transaction_id)
    if not txn or txn.deleted_at is not None or txn.portfolio_id != portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    txn.memo = body.memo
    if body.tags is not None:
        txn.tags = body.tags
    await db.commit()
    await db.refresh(txn)
    return txn


@router.get("/{portfolio_id}/kis-transactions")
async def list_kis_transactions(
    portfolio_id: int,
    from_date: str = Query(..., pattern=r"^\d{8}$", description="YYYYMMDD"),
    to_date: str = Query(..., pattern=r"^\d{8}$", description="YYYYMMDD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """KIS API에서 체결 내역 조회 (국내 + 해외). KIS 계정 연결 필요."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    _assert_portfolio_owner(portfolio, current_user)

    if not portfolio.kis_account_id:
        return []

    acct = await db.get(KisAccount, portfolio.kis_account_id)
    if not acct:
        return []

    from app.services.kis_transaction import fetch_domestic_transactions, fetch_overseas_transactions

    try:
        app_key = decrypt(acct.app_key_enc)
        app_secret = decrypt(acct.app_secret_enc)
        async with httpx.AsyncClient(timeout=15.0) as client:
            domestic, overseas = await asyncio.gather(
                fetch_domestic_transactions(
                    app_key, app_secret, acct.account_no, acct.acnt_prdt_cd,
                    from_date, to_date, client,
                ),
                fetch_overseas_transactions(
                    app_key, app_secret, acct.account_no, acct.acnt_prdt_cd,
                    from_date, to_date, client,
                ),
                return_exceptions=True,
            )
        results: list[dict] = []
        if isinstance(domestic, list):
            results.extend(domestic)
        if isinstance(overseas, list):
            results.extend(overseas)
        results.sort(key=lambda x: x.get("traded_at", ""), reverse=True)
        return results
    except Exception as e:
        logger.warning("KIS transaction fetch failed for portfolio %d: %s", portfolio_id, e)
        return []
