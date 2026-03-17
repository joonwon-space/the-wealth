"""KIS 계좌 자동 동기화 API."""

import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.sync_log import SyncLog
from app.models.user import User
from app.services.kis_account import KisHolding, fetch_account_holdings
from app.services.kis_token import get_kis_access_token, invalidate_kis_token
from app.services.reconciliation import reconcile_holdings

router = APIRouter(prefix="/sync", tags=["sync"])
logger = logging.getLogger(__name__)


async def _fetch_balance_raw(
    acct: KisAccount, *, _retried: bool = False
) -> tuple[dict, list[KisHolding]]:
    """단일 KIS 계좌의 원시 잔고 + holdings 조회.

    500/401 응답 시 토큰을 무효화하고 최초 1회 재시도한다.
    """
    app_key = decrypt(acct.app_key_enc)
    app_secret = decrypt(acct.app_secret_enc)
    token = await get_kis_access_token(app_key, app_secret)

    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "TTTC8434R",
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "CANO": acct.account_no,
        "ACNT_PRDT_CD": acct.acnt_prdt_cd,
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

    if resp.status_code in (401, 500) and not _retried:
        logger.warning(
            "KIS balance API returned %d for %s-%s — invalidating token and retrying",
            resp.status_code,
            acct.account_no,
            acct.acnt_prdt_cd,
        )
        await invalidate_kis_token(app_key)
        return await _fetch_balance_raw(acct, _retried=True)

    resp.raise_for_status()
    data = resp.json()

    rt_cd = data.get("rt_cd")
    if rt_cd != "0":
        msg = data.get("msg1", "Unknown KIS API error")
        logger.error(
            "KIS API error for account %s-%s: rt_cd=%s msg=%s",
            acct.account_no,
            acct.acnt_prdt_cd,
            rt_cd,
            msg,
        )
        raise RuntimeError(f"KIS API 오류 (rt_cd={rt_cd}): {msg}")

    summary = (data.get("output2") or [{}])[0]
    holdings_list = await fetch_account_holdings(
        app_key, app_secret, acct.account_no, acct.acnt_prdt_cd
    )

    return summary, holdings_list


async def _ensure_portfolio_for_account(
    db: AsyncSession, user_id: int, acct: KisAccount
) -> Portfolio:
    """KIS 계좌에 연결된 포트폴리오가 없으면 자동 생성."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.kis_account_id == acct.id)
    )
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        portfolio = Portfolio(
            user_id=user_id,
            name=acct.label,
            currency="KRW",
            kis_account_id=acct.id,
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
        logger.info(
            "Auto-created portfolio '%s' for KIS account %s-%s",
            acct.label,
            acct.account_no,
            acct.acnt_prdt_cd,
        )

    return portfolio


@router.post("/balance")
async def get_account_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """모든 KIS 계좌 잔고 조회 + 포트폴리오 자동 생성 + holdings 동기화."""
    result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id)
    )
    accounts = list(result.scalars().all())

    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No KIS accounts configured",
        )

    # 병렬로 모든 계좌 잔고 조회
    raw_results = await asyncio.gather(
        *[_fetch_balance_raw(acct) for acct in accounts],
        return_exceptions=True,
    )

    account_results = []
    for acct, raw in zip(accounts, raw_results):
        if isinstance(raw, Exception):
            logger.warning(
                "Balance inquiry failed for %s: %s", acct.label, raw, exc_info=raw
            )
            account_results.append(
                {
                    "label": acct.label,
                    "account_no": f"{acct.account_no}-{acct.acnt_prdt_cd}",
                    "error": "잔고 조회에 실패했습니다. 잠시 후 다시 시도해주세요.",
                    "deposit": "0",
                    "total_eval": "0",
                    "stock_eval": "0",
                    "pnl": "0",
                    "holdings": [],
                }
            )
            continue

        summary, kis_holdings = raw

        # 포트폴리오 자동 생성
        portfolio = await _ensure_portfolio_for_account(db, current_user.id, acct)

        # holdings 동기화
        counts = await reconcile_holdings(db, portfolio.id, kis_holdings)
        has_changes = counts["inserted"] or counts["updated"] or counts["deleted"]

        # SyncLog 항상 기록
        log = SyncLog(
            user_id=current_user.id,
            portfolio_id=portfolio.id,
            status="success",
            inserted=counts["inserted"],
            updated=counts["updated"],
            deleted=counts["deleted"],
            message=None if has_changes else "no changes",
        )
        db.add(log)
        await db.commit()

        if has_changes:
            logger.info(
                "Auto-synced %s: +%d ~%d -%d",
                acct.label,
                counts["inserted"],
                counts["updated"],
                counts["deleted"],
            )

        account_results.append(
            {
                "label": acct.label,
                "account_no": f"{acct.account_no}-{acct.acnt_prdt_cd}",
                "portfolio_id": portfolio.id,
                "deposit": summary.get("dnca_tot_amt", "0"),
                "total_eval": summary.get("tot_evlu_amt", "0"),
                "stock_eval": summary.get("scts_evlu_amt", "0"),
                "pnl": summary.get("evlu_pfls_smtl_amt", "0"),
                "synced": counts,
                "holdings": [
                    {
                        "ticker": h.ticker,
                        "name": h.name,
                        "quantity": str(h.quantity),
                        "avg_price": str(h.avg_price),
                    }
                    for h in kis_holdings
                ],
            }
        )

    return {"accounts": account_results}


@router.post("/{portfolio_id}")
async def sync_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """포트폴리오에 연결된 KIS 계좌로 동기화."""
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio or portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )

    if not portfolio.kis_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio not linked to a KIS account",
        )

    acct = await db.get(KisAccount, portfolio.kis_account_id)
    if not acct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="KIS account not found"
        )

    app_key = decrypt(acct.app_key_enc)
    app_secret = decrypt(acct.app_secret_enc)

    try:
        kis_holdings = await fetch_account_holdings(
            app_key, app_secret, acct.account_no, acct.acnt_prdt_cd
        )
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
        logger.error(
            "Sync error for portfolio %d: %s", portfolio_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="동기화에 실패했습니다. 잠시 후 다시 시도해주세요.",
        ) from exc


@router.get("/logs")
async def get_sync_logs(
    offset: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(SyncLog)
        .where(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.synced_at.desc())
        .offset(offset)
        .limit(min(limit, 100))
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
