"""Operations scheduler jobs.

Contains order settlement job.
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
from app.services.order_settlement import settle_pending_orders

logger = get_logger(__name__)


async def settle_orders_job(
    record_success: Callable[[str], None],
    record_failure: Callable[[str, Exception], None],
    job_id: str = "settle_orders",
) -> None:
    """미체결 주문의 체결 여부를 KIS API로 확인하고 반영.

    장중(KST 09:05~15:35) 5분 간격 실행.
    """
    logger.info("[Scheduler] Starting pending order settlement check")

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(KisAccount))
            kis_accounts = cast(list[KisAccount], result.scalars().all())

            if not kis_accounts:
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

                    counts = await settle_pending_orders(
                        db=db,
                        portfolio_id=portfolio.id,
                        app_key=app_key,
                        app_secret=app_secret,
                        account_no=acct.account_no,
                        account_product_code=acct.acnt_prdt_cd,
                        is_paper_trading=acct.is_paper_trading,
                    )

                    if counts["settled"] > 0 or counts["partial"] > 0:
                        logger.info(
                            "[Scheduler] Settlement user=%d portfolio=%d: "
                            "settled=%d partial=%d unchanged=%d",
                            acct.user_id,
                            portfolio.id,
                            counts["settled"],
                            counts["partial"],
                            counts["unchanged"],
                        )
                except Exception as exc:
                    logger.warning(
                        "[Scheduler] Settlement failed user=%d: %s",
                        acct.user_id,
                        exc,
                    )

        record_success(job_id)

    except Exception as exc:
        record_failure(job_id, exc)
