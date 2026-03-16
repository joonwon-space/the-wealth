"""KIS 계좌 자동 동기화 API."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.portfolio import Portfolio
from app.models.sync_log import SyncLog
from app.models.user import User
from app.services.kis_account import fetch_account_holdings
from app.services.reconciliation import reconcile_holdings

router = APIRouter(prefix="/sync", tags=["sync"])
logger = logging.getLogger(__name__)


@router.post("/{portfolio_id}")
async def sync_portfolio(
    portfolio_id: int,
    account_no: str = Query(..., description="KIS 계좌번호 (CANO)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """KIS 계좌 잔고를 조회해 DB holdings와 Reconcile."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio or portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    if not current_user.kis_app_key_enc or not current_user.kis_app_secret_enc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KIS credentials not configured")

    app_key = decrypt(current_user.kis_app_key_enc)
    app_secret = decrypt(current_user.kis_app_secret_enc)

    try:
        kis_holdings = await fetch_account_holdings(app_key, app_secret, account_no)
        counts = await reconcile_holdings(db, portfolio_id, kis_holdings)

        log = SyncLog(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            status="success",
            inserted=counts["inserted"],
            updated=counts["updated"],
            deleted=counts["deleted"],
        )
        db.add(log)
        await db.commit()
        return {"status": "success", **counts}
    except Exception as exc:
        log = SyncLog(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            status="error",
            message=str(exc)[:500],
        )
        db.add(log)
        await db.commit()
        logger.error("Sync error for portfolio %d: %s", portfolio_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/logs")
async def get_sync_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(SyncLog)
        .where(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.synced_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "portfolio_id": log.portfolio_id,
            "status": log.status,
            "inserted": log.inserted,
            "updated": log.updated,
            "deleted": log.deleted,
            "message": log.message,
            "synced_at": log.synced_at.isoformat(),
        }
        for log in logs
    ]
