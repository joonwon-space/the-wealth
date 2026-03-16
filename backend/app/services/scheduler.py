"""APScheduler 기반 자동 동기화 스케줄러.

FastAPI 앱 startup/shutdown 이벤트에 연결하여 사용합니다.
KIS 자격증명이 등록된 사용자의 첫 번째 포트폴리오를 1시간 간격으로 동기화.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.encryption import decrypt
from app.db.session import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.models.sync_log import SyncLog
from app.models.user import User
from app.services.kis_account import fetch_account_holdings
from app.services.reconciliation import reconcile_holdings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _sync_all_accounts() -> None:
    """KIS 자격증명이 있는 모든 사용자의 계좌를 순차 동기화."""
    logger.info("[Scheduler] Starting periodic KIS account sync")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.kis_app_key_enc.isnot(None),
                User.kis_app_secret_enc.isnot(None),
                User.kis_account_no.isnot(None),
            )
        )
        users = list(result.scalars().all())

        if not users:
            logger.info("[Scheduler] No users with KIS credentials, skipping")
            return

        for user in users:
            portfolio_result = await db.execute(
                select(Portfolio)
                .where(Portfolio.user_id == user.id)
                .order_by(Portfolio.id)
                .limit(1)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            if not portfolio:
                continue

            try:
                app_key = decrypt(user.kis_app_key_enc)
                app_secret = decrypt(user.kis_app_secret_enc)
                account_no = user.kis_account_no

                kis_holdings = await fetch_account_holdings(
                    app_key, app_secret, account_no
                )
                counts = await reconcile_holdings(db, portfolio.id, kis_holdings)

                log_entry = SyncLog(
                    user_id=user.id,
                    portfolio_id=portfolio.id,
                    status="success",
                    inserted=counts["inserted"],
                    updated=counts["updated"],
                    deleted=counts["deleted"],
                )
                db.add(log_entry)
                await db.commit()

                logger.info(
                    "[Scheduler] Synced user=%d portfolio=%d: +%d ~%d -%d",
                    user.id,
                    portfolio.id,
                    counts["inserted"],
                    counts["updated"],
                    counts["deleted"],
                )
            except Exception as exc:
                log_entry = SyncLog(
                    user_id=user.id,
                    portfolio_id=portfolio.id,
                    status="error",
                    message=str(exc)[:500],
                )
                db.add(log_entry)
                await db.commit()
                logger.warning(
                    "[Scheduler] Sync failed user=%d: %s", user.id, exc
                )


def start_scheduler() -> None:
    scheduler.add_job(
        _sync_all_accounts,
        trigger="interval",
        hours=1,
        id="kis_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] APScheduler started — KIS sync every 1 hour")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("[Scheduler] APScheduler stopped")
