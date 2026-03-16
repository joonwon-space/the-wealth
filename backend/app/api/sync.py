"""KIS 계좌 자동 동기화 API."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.portfolio import Portfolio
from app.models.sync_log import SyncLog
from app.models.user import User
from app.services.kis_account import fetch_account_holdings
from app.services.kis_token import get_kis_access_token
from app.services.reconciliation import reconcile_holdings

router = APIRouter(prefix="/sync", tags=["sync"])
logger = logging.getLogger(__name__)


@router.get("/balance")
async def get_account_balance(
    current_user: User = Depends(get_current_user),
) -> dict:
    """KIS 실계좌 잔고를 조회만 한다 (동기화 없음)."""
    if not current_user.kis_app_key_enc or not current_user.kis_app_secret_enc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KIS credentials not configured")
    if not current_user.kis_account_no:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account number not configured")

    app_key = decrypt(current_user.kis_app_key_enc)
    app_secret = decrypt(current_user.kis_app_secret_enc)
    acnt_prdt_cd = current_user.kis_acnt_prdt_cd or "01"

    try:
        token = await get_kis_access_token(app_key, app_secret)
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "TTTC8434R",
            "Content-Type": "application/json; charset=utf-8",
        }
        params = {
            "CANO": current_user.kis_account_no,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        output2 = data.get("output2", [{}])
        summary = output2[0] if output2 else {}

        holdings_list = await fetch_account_holdings(app_key, app_secret, current_user.kis_account_no, acnt_prdt_cd)
        return {
            "account_no": current_user.kis_account_no,
            "deposit": summary.get("dnca_tot_amt", "0"),
            "total_eval": summary.get("tot_evlu_amt", "0"),
            "stock_eval": summary.get("scts_evlu_amt", "0"),
            "pnl": summary.get("evlu_pfls_smtl_amt", "0"),
            "holdings": [
                {
                    "ticker": h.ticker,
                    "name": h.name,
                    "quantity": str(h.quantity),
                    "avg_price": str(h.avg_price),
                }
                for h in holdings_list
            ],
        }
    except Exception as exc:
        logger.error("Balance inquiry failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/{portfolio_id}")
async def sync_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """KIS 계좌 잔고를 조회해 DB holdings와 Reconcile. 계좌번호는 DB에서 자동 사용."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio or portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    if not current_user.kis_app_key_enc or not current_user.kis_app_secret_enc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KIS credentials not configured")
    if not current_user.kis_account_no:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account number not configured")

    app_key = decrypt(current_user.kis_app_key_enc)
    app_secret = decrypt(current_user.kis_app_secret_enc)
    acnt_prdt_cd = current_user.kis_acnt_prdt_cd or "01"

    try:
        kis_holdings = await fetch_account_holdings(app_key, app_secret, current_user.kis_account_no, acnt_prdt_cd)
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
