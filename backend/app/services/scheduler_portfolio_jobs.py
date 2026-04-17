"""Portfolio synchronization scheduler jobs.

Contains KIS account sync (holdings reconciliation) job.
Imported and registered by app.services.scheduler.
"""

from collections.abc import Callable
from typing import cast

from sqlalchemy import select

from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.sync_log import SyncLog
from app.services.kis_account import fetch_account_holdings, fetch_overseas_account_holdings
from app.services.reconciliation import reconcile_holdings

logger = get_logger(__name__)


async def sync_all_accounts(
    record_success: Callable[[str], None],
    record_failure: Callable[[str, Exception], None],
    job_id: str = "kis_sync_us",
) -> None:
    """KIS 계좌가 등록된 모든 포트폴리오를 순차 동기화."""
    logger.info("[Scheduler] Starting periodic KIS account sync")

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(KisAccount))
            kis_accounts = cast(list[KisAccount], result.scalars().all())

            if not kis_accounts:
                logger.info("[Scheduler] No KIS accounts found, skipping")
                record_success(job_id)
                return

            for acct in kis_accounts:
                portfolio_result = await db.execute(
                    select(Portfolio)
                    .where(Portfolio.kis_account_id == acct.id)
                    .limit(1)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                if not portfolio:
                    continue

                try:
                    app_key = decrypt(acct.app_key_enc)
                    app_secret = decrypt(acct.app_secret_enc)
                    account_no = acct.account_no

                    domestic_holdings = await fetch_account_holdings(
                        app_key, app_secret, account_no, acct.acnt_prdt_cd
                    )
                    overseas_holdings, _ = await fetch_overseas_account_holdings(
                        app_key, app_secret, account_no, acct.acnt_prdt_cd
                    )
                    kis_holdings = domestic_holdings + overseas_holdings
                    counts = await reconcile_holdings(db, portfolio.id, kis_holdings)

                    log_entry = SyncLog(
                        user_id=acct.user_id,
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
                        acct.user_id,
                        portfolio.id,
                        counts["inserted"],
                        counts["updated"],
                        counts["deleted"],
                    )
                except Exception as exc:
                    log_entry = SyncLog(
                        user_id=acct.user_id,
                        portfolio_id=portfolio.id,
                        status="error",
                        message=str(exc)[:500],
                    )
                    db.add(log_entry)
                    await db.commit()
                    logger.warning("[Scheduler] Sync failed user=%d: %s", acct.user_id, exc)

        record_success(job_id)

    except Exception as exc:
        record_failure(job_id, exc)
