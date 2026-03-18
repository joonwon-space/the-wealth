"""APScheduler 기반 자동 동기화 스케줄러.

FastAPI 앱 startup/shutdown 이벤트에 연결하여 사용합니다.
KIS 자격증명이 등록된 사용자의 첫 번째 포트폴리오를 1시간 간격으로 동기화.
장 마감(KST 16:10) 후 보유 종목 OHLCV를 price_snapshots에 저장.
"""

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.sync_log import SyncLog
from app.services.kis_account import fetch_account_holdings
from app.services.kis_price import fetch_domestic_daily_ohlcv, fetch_domestic_price
from app.services.price_snapshot import OhlcvData, save_ohlcv_snapshots, save_snapshots
from app.services.reconciliation import reconcile_holdings

logger = get_logger(__name__)

scheduler = AsyncIOScheduler()


async def _sync_all_accounts() -> None:
    """KIS 계좌가 등록된 모든 포트폴리오를 순차 동기화."""
    logger.info("[Scheduler] Starting periodic KIS account sync")

    async with AsyncSessionLocal() as db:
        # KIS 계좌가 연결된 포트폴리오를 KisAccount 테이블에서 조회
        result = await db.execute(select(KisAccount))
        kis_accounts = list(result.scalars().all())

        if not kis_accounts:
            logger.info("[Scheduler] No KIS accounts found, skipping")
            return

        for acct in kis_accounts:  # type: ignore[assignment]
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

                kis_holdings = await fetch_account_holdings(
                    app_key, app_secret, account_no
                )
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


async def _snapshot_daily_close() -> None:
    """장 마감 후 보유 종목 OHLCV를 price_snapshots에 저장.

    KST 16:10 (UTC 07:10) 평일 실행.
    """
    import asyncio
    from decimal import Decimal

    logger.info("[Scheduler] Starting daily close snapshot")

    async with AsyncSessionLocal() as db:
        # 모든 KIS 계좌 중 첫 번째 계정 크리덴셜 사용
        acct_result = await db.execute(select(KisAccount).limit(1))
        acct = acct_result.scalar_one_or_none()
        if not acct:
            logger.info("[Scheduler] No KIS accounts found, skipping snapshot")
            return

        app_key = decrypt(acct.app_key_enc)
        app_secret = decrypt(acct.app_secret_enc)

        # 전체 보유 종목 ticker 수집
        hold_result = await db.execute(select(Holding.ticker).distinct())
        tickers = [row[0] for row in hold_result.all()]
        if not tickers:
            logger.info("[Scheduler] No holdings found, skipping snapshot")
            return

        # 일별 OHLCV 병렬 조회
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await asyncio.gather(
                *[fetch_domestic_daily_ohlcv(t, app_key, app_secret, client) for t in tickers],
                return_exceptions=True,
            )

        ohlcv_map: dict[str, OhlcvData] = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, dict) and result.get("close"):
                ohlcv_map[ticker] = OhlcvData(
                    open=result.get("open"),
                    high=result.get("high"),
                    low=result.get("low"),
                    close=result["close"],
                    volume=result.get("volume"),
                )

        if ohlcv_map:
            count = await save_ohlcv_snapshots(db, ohlcv_map)
        else:
            # OHLCV 조회 실패 시 현재가 폴백
            prices: dict[str, Decimal] = {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                price_results = await asyncio.gather(
                    *[fetch_domestic_price(t, app_key, app_secret, client) for t in tickers],
                    return_exceptions=True,
                )
            for ticker, price in zip(tickers, price_results):
                if isinstance(price, Decimal) and price > 0:
                    prices[ticker] = price
            count = await save_snapshots(db, prices)

        logger.info("[Scheduler] Saved %d price snapshots", count)


def start_scheduler() -> None:
    scheduler.add_job(
        _sync_all_accounts,
        trigger="interval",
        hours=1,
        id="kis_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _snapshot_daily_close,
        trigger="cron",
        day_of_week="mon-fri",
        hour=7,
        minute=10,
        timezone="UTC",
        id="daily_close_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] APScheduler started — KIS sync every 1 hour, daily close snapshot at KST 16:10")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=True)
    logger.info("[Scheduler] APScheduler stopped (waited for running jobs)")
