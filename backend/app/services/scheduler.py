"""APScheduler 기반 자동 동기화 스케줄러.

FastAPI 앱 startup/shutdown 이벤트에 연결하여 사용합니다.
KIS 자격증명이 등록된 사용자의 첫 번째 포트폴리오를 1시간 간격으로 동기화.
장 마감(KST 16:10) 후 보유 종목 OHLCV를 price_snapshots에 저장.

연속 실패 감지: 각 스케줄러 잡이 CONSECUTIVE_FAILURE_THRESHOLD 회 이상 연속으로
실패하면 CRITICAL 레벨 로그를 남겨 운영자가 인지할 수 있도록 한다.
"""

import asyncio
from decimal import Decimal

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
from app.services.kis_price import (
    fetch_domestic_daily_ohlcv,
    fetch_domestic_price,
    fetch_and_cache_domestic_price,
    fetch_usd_krw_rate,
    get_or_fetch_overseas_price,
    save_fx_rate_snapshot,
)
from app.services.price_snapshot import OhlcvData, save_ohlcv_snapshots, save_snapshots
from app.services.reconciliation import reconcile_holdings

logger = get_logger(__name__)

scheduler = AsyncIOScheduler()

# Consecutive failure threshold before CRITICAL alert is emitted
CONSECUTIVE_FAILURE_THRESHOLD = 3

# In-memory consecutive failure counters, keyed by job id
_consecutive_failures: dict[str, int] = {
    "kis_sync_kr": 0,
    "kis_sync_us": 0,
    "daily_close_snapshot": 0,
    "fx_rate_snapshot": 0,
    "preload_prices": 0,
}


def _record_job_success(job_id: str) -> None:
    """Reset consecutive failure counter on successful job execution."""
    _consecutive_failures[job_id] = 0


def _record_job_failure(job_id: str, exc: Exception) -> None:
    """Increment consecutive failure counter and emit CRITICAL log at threshold."""
    count = _consecutive_failures.get(job_id, 0) + 1
    _consecutive_failures[job_id] = count
    logger.warning(
        "[Scheduler] Job '%s' failed (consecutive=%d): %s",
        job_id,
        count,
        exc,
    )
    if count >= CONSECUTIVE_FAILURE_THRESHOLD:
        logger.critical(
            "[Scheduler] ALERT: job '%s' has failed %d consecutive times. "
            "Immediate investigation required. Last error: %s",
            job_id,
            count,
            exc,
        )


async def _sync_all_accounts(job_id: str = "kis_sync_kr") -> None:
    """KIS 계좌가 등록된 모든 포트폴리오를 순차 동기화."""
    logger.info("[Scheduler] Starting periodic KIS account sync")

    try:
        async with AsyncSessionLocal() as db:
            # KIS 계좌가 연결된 포트폴리오를 KisAccount 테이블에서 조회
            result = await db.execute(select(KisAccount))
            kis_accounts = list(result.scalars().all())

            if not kis_accounts:
                logger.info("[Scheduler] No KIS accounts found, skipping")
                _record_job_success(job_id)
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

        _record_job_success(job_id)

    except Exception as exc:
        _record_job_failure(job_id, exc)


async def _snapshot_daily_close() -> None:
    """장 마감 후 보유 종목 OHLCV를 price_snapshots에 저장.

    KST 16:10 (UTC 07:10) 평일 실행.
    """
    import asyncio
    from decimal import Decimal

    job_id = "daily_close_snapshot"
    logger.info("[Scheduler] Starting daily close snapshot")

    try:
        async with AsyncSessionLocal() as db:
            # 모든 KIS 계좌 중 첫 번째 계정 크리덴셜 사용
            acct_result = await db.execute(select(KisAccount).limit(1))
            acct = acct_result.scalar_one_or_none()
            if not acct:
                logger.info("[Scheduler] No KIS accounts found, skipping snapshot")
                _record_job_success(job_id)
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)

            # 전체 보유 종목 ticker 수집
            hold_result = await db.execute(select(Holding.ticker).distinct())
            tickers = [row[0] for row in hold_result.all()]
            if not tickers:
                logger.info("[Scheduler] No holdings found, skipping snapshot")
                _record_job_success(job_id)
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

        _record_job_success(job_id)

    except Exception as exc:
        _record_job_failure(job_id, exc)


_DOMESTIC_TICKER_RE_SCHED = __import__("re").compile(r"^[0-9A-Z]{6}$")
_MARKET_MAP_SCHED = {
    "NASD": "NAS", "NYSE": "NYS", "AMEX": "AMS",
    "SEHK": "HKS", "TKSE": "TSE", "SHAA": "SHS",
    "SZAA": "SZS", "HASE": "HNX", "VNSE": "HSX",
}


async def _preload_prices(job_id: str = "preload_prices") -> None:
    """장 개시 전 보유 종목을 KIS에서 동기화한 뒤 가격 캐시를 워밍.

    KST 08:00 평일 실행:
    1. 모든 KIS 계좌의 보유 종목을 reconcile_holdings로 최신화 (어제 종가 이후 변동 반영)
    2. 갱신된 보유 종목 전체의 가격을 Redis에 캐싱 (접속 시 즉시 최신 가격 제공)
    """
    logger.info("[Scheduler] Starting pre-market holdings sync + price preload")
    try:
        # Step 1: holdings 동기화 (모든 KIS 계좌)
        await _sync_all_accounts(job_id=job_id)
        logger.info("[Scheduler] Pre-market holdings sync complete, starting price preload")

        # Step 2: 갱신된 holdings 기준으로 가격 캐시 워밍
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(KisAccount).limit(1))
            acct = result.scalar_one_or_none()
            if not acct:
                logger.info("[Scheduler] No KIS account found, skipping preload")
                _record_job_success(job_id)
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)

            hold_result = await db.execute(
                select(Holding.ticker, Holding.market).distinct()
            )
            rows = hold_result.all()

        if not rows:
            logger.info("[Scheduler] No holdings found, skipping preload")
            _record_job_success(job_id)
            return

        domestic = [r[0] for r in rows if _DOMESTIC_TICKER_RE_SCHED.match(r[0])]
        overseas = [(r[0], r[1]) for r in rows if not _DOMESTIC_TICKER_RE_SCHED.match(r[0])]

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
                fetch_and_cache_domestic_price(t, app_key, app_secret, client)
                for t in domestic
            ] + [
                get_or_fetch_overseas_price(
                    t, _MARKET_MAP_SCHED.get(m or "", "NAS"), app_key, app_secret, client
                )
                for t, m in overseas
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        success = sum(1 for r in results if isinstance(r, Decimal) and r > 0)
        logger.info(
            "[Scheduler] Pre-market preload complete: %d/%d tickers cached",
            success,
            len(rows),
        )
        _record_job_success(job_id)
    except Exception as exc:
        _record_job_failure(job_id, exc)


async def _save_fx_rate_snapshot(job_id: str = "fx_rate_snapshot") -> None:
    """장 마감 후 USD/KRW 환율을 조회해 fx_rate_snapshots에 저장.

    KST 16:30 (UTC 07:30) 실행 — 한국 장 마감 후 당일 환율을 기록한다.
    KIS 자격증명이 없으면 frankfurter.app을 통해 환율을 조회한다.
    """
    logger.info("[Scheduler] Starting FX rate snapshot job")
    try:
        async with AsyncSessionLocal() as db:
            # KIS 자격증명 조회 (선택적)
            result = await db.execute(select(KisAccount).limit(1))
            acct = result.scalar_one_or_none()

            if acct:
                app_key = decrypt(acct.app_key_enc)
                app_secret = decrypt(acct.app_secret_enc)
            else:
                app_key = ""
                app_secret = ""

            async with httpx.AsyncClient(timeout=10.0) as client:
                rate = await fetch_usd_krw_rate(app_key, app_secret, client)

            saved = await save_fx_rate_snapshot(db, "USDKRW", float(rate))
            if saved:
                logger.info("[Scheduler] FX rate snapshot saved: USDKRW = %s", rate)
            else:
                logger.warning("[Scheduler] FX rate snapshot save failed")

        _record_job_success(job_id)
    except Exception as exc:
        _record_job_failure(job_id, exc)


def start_scheduler() -> None:
    # 국내 장 마감 후 동기화: KST 16:00 = UTC 07:00
    scheduler.add_job(
        _sync_all_accounts,
        trigger="cron",
        day_of_week="mon-fri",
        hour=7,
        minute=0,
        timezone="UTC",
        id="kis_sync_kr",
        kwargs={"job_id": "kis_sync_kr"},
        replace_existing=True,
    )
    # 미국 장 마감 후 동기화: EST 16:00 ≈ UTC 21:00 (= KST 06:00)
    scheduler.add_job(
        _sync_all_accounts,
        trigger="cron",
        day_of_week="mon-fri",
        hour=21,
        minute=30,
        timezone="UTC",
        id="kis_sync_us",
        kwargs={"job_id": "kis_sync_us"},
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
    # 장 개시 전 가격 캐시 워밍: KST 08:00 평일
    scheduler.add_job(
        _preload_prices,
        trigger="cron",
        day_of_week="mon-fri",
        hour=8,
        minute=0,
        timezone="Asia/Seoul",
        id="preload_prices",
        kwargs={"job_id": "preload_prices"},
        replace_existing=True,
    )
    # 장 마감 후 환율 스냅샷: KST 16:30 = UTC 07:30 평일
    scheduler.add_job(
        _save_fx_rate_snapshot,
        trigger="cron",
        day_of_week="mon-fri",
        hour=7,
        minute=30,
        timezone="UTC",
        id="fx_rate_snapshot",
        kwargs={"job_id": "fx_rate_snapshot"},
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "[Scheduler] APScheduler started — KIS sync at KST 16:00 (KR close) & 06:30 (US close), "
        "daily close snapshot at KST 16:10, FX snapshot at KST 16:30, price preload at KST 08:00"
    )


def stop_scheduler() -> None:
    scheduler.shutdown(wait=True)
    logger.info("[Scheduler] APScheduler stopped (waited for running jobs)")
