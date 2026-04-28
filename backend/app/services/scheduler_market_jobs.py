"""Market-data scheduler jobs.

Contains daily close snapshot, price preload, FX rate snapshot, and benchmark
collection jobs. Imported and registered by app.services.scheduler.
"""

import asyncio
import re
from collections.abc import Awaitable, Callable
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.services.kis_price import (
    fetch_domestic_daily_ohlcv,
    fetch_domestic_price,
    fetch_and_cache_domestic_price,
    fetch_overseas_daily_ohlcv,
    fetch_overseas_price,
    fetch_usd_krw_rate,
    get_or_fetch_overseas_price,
    save_fx_rate_snapshot,
)
from app.services.price_snapshot import OhlcvData, save_ohlcv_snapshots, save_snapshots

logger = get_logger(__name__)

_DOMESTIC_TICKER_RE_SCHED = re.compile(r"^[0-9A-Z]{6}$")
_MARKET_MAP_SCHED = {
    "NASD": "NAS", "NYSE": "NYS", "AMEX": "AMS",
    "SEHK": "HKS", "TKSE": "TSE", "SHAA": "SHS",
    "SZAA": "SZS", "HASE": "HNX", "VNSE": "HSX",
}


async def snapshot_daily_close(
    record_success: Callable[[str], None],
    record_failure: Callable[[str, Exception], None],
    job_id: str = "daily_close_snapshot",
) -> None:
    """장 마감 후 보유 종목 OHLCV를 price_snapshots에 저장.

    KST 16:10 (UTC 07:10) 평일 실행.
    """
    logger.info("[Scheduler] Starting daily close snapshot")

    try:
        async with AsyncSessionLocal() as db:
            acct_result = await db.execute(select(KisAccount).limit(1))
            acct = acct_result.scalar_one_or_none()
            if not acct:
                logger.info("[Scheduler] No KIS accounts found, skipping snapshot")
                record_success(job_id)
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)

            hold_result = await db.execute(
                select(Holding.ticker, Holding.market).distinct()
            )
            rows = hold_result.all()
            if not rows:
                logger.info("[Scheduler] No holdings found, skipping snapshot")
                record_success(job_id)
                return

            domestic = [r[0] for r in rows if _DOMESTIC_TICKER_RE_SCHED.match(r[0])]
            overseas = [
                (r[0], r[1])
                for r in rows
                if not _DOMESTIC_TICKER_RE_SCHED.match(r[0])
            ]

            async with httpx.AsyncClient(timeout=10.0) as client:
                domestic_results = await asyncio.gather(
                    *[
                        fetch_domestic_daily_ohlcv(t, app_key, app_secret, client)
                        for t in domestic
                    ],
                    return_exceptions=True,
                )
                overseas_results = await asyncio.gather(
                    *[
                        fetch_overseas_daily_ohlcv(
                            t,
                            _MARKET_MAP_SCHED.get(m or "", "NAS"),
                            app_key,
                            app_secret,
                            client,
                        )
                        for t, m in overseas
                    ],
                    return_exceptions=True,
                )

            all_tickers = domestic + [t for t, _ in overseas]
            all_results = list(domestic_results) + list(overseas_results)

            ohlcv_map: dict[str, OhlcvData] = {}
            for ticker, result in zip(all_tickers, all_results):
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
                prices: dict[str, Decimal] = {}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    dom_price_results = await asyncio.gather(
                        *[
                            fetch_domestic_price(t, app_key, app_secret, client)
                            for t in domestic
                        ],
                        return_exceptions=True,
                    )
                    ovs_price_results = await asyncio.gather(
                        *[
                            fetch_overseas_price(
                                t,
                                _MARKET_MAP_SCHED.get(m or "", "NAS"),
                                app_key,
                                app_secret,
                                client,
                            )
                            for t, m in overseas
                        ],
                        return_exceptions=True,
                    )
                for ticker, price in zip(domestic, dom_price_results):
                    if isinstance(price, Decimal) and price > 0:
                        prices[ticker] = price
                for (ticker, _), price in zip(overseas, ovs_price_results):
                    if isinstance(price, Decimal) and price > 0:
                        prices[ticker] = price
                count = await save_snapshots(db, prices)

            logger.info("[Scheduler] Saved %d price snapshots", count)

        record_success(job_id)

    except Exception as exc:
        record_failure(job_id, exc)


async def preload_prices(
    sync_all_accounts: Callable[..., Awaitable[None]],
    record_success: Callable[[str], None],
    record_failure: Callable[[str, Exception], None],
    job_id: str = "preload_prices",
) -> None:
    """장 개시 전 보유 종목을 KIS에서 동기화한 뒤 가격 캐시를 워밍.

    KST 08:00 평일 실행:
    1. 모든 KIS 계좌의 보유 종목을 reconcile_holdings로 최신화
    2. 갱신된 보유 종목 전체의 가격을 Redis에 캐싱
    """
    logger.info("[Scheduler] Starting pre-market holdings sync + price preload")
    try:
        await sync_all_accounts(job_id=job_id)
        logger.info("[Scheduler] Pre-market holdings sync complete, starting price preload")

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(KisAccount).limit(1))
            acct = result.scalar_one_or_none()
            if not acct:
                logger.info("[Scheduler] No KIS account found, skipping preload")
                record_success(job_id)
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)

            hold_result = await db.execute(
                select(Holding.ticker, Holding.market).distinct()
            )
            rows = hold_result.all()

        if not rows:
            logger.info("[Scheduler] No holdings found, skipping preload")
            record_success(job_id)
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
        record_success(job_id)
    except Exception as exc:
        record_failure(job_id, exc)


async def save_fx_rate_snapshot_job(
    record_success: Callable[[str], None],
    record_failure: Callable[[str, Exception], None],
    job_id: str = "fx_rate_snapshot",
) -> None:
    """장 마감 후 USD/KRW 환율을 조회해 fx_rate_snapshots에 저장.

    KST 16:30 (UTC 07:30) 실행.
    """
    logger.info("[Scheduler] Starting FX rate snapshot job")
    try:
        async with AsyncSessionLocal() as db:
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

        record_success(job_id)
    except Exception as exc:
        record_failure(job_id, exc)


async def collect_benchmark_snapshots(
    record_success: Callable[[str], None],
    record_failure: Callable[[str, Exception], None],
    job_id: str = "collect_benchmark",
) -> None:
    """KOSPI200 + S&P500 지수 스냅샷 수집 후 index_snapshots에 저장.

    KST 16:20 평일 실행 (국내 장 마감 후).
    """
    from app.services.kis_benchmark import collect_snapshots

    logger.info("[Scheduler] Starting benchmark snapshot collection")

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(KisAccount).limit(1))
            acct = result.scalar_one_or_none()
            if not acct:
                logger.info("[Scheduler] No KIS account found, skipping benchmark collection")
                record_success(job_id)
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)

        status = await collect_snapshots(app_key, app_secret)
        logger.info("[Scheduler] Benchmark collection results: %s", status)

        if any(status.values()):
            record_success(job_id)
        else:
            record_failure(job_id, RuntimeError("All benchmark fetches failed"))

    except Exception as exc:
        record_failure(job_id, exc)


async def collect_dividends_job(
    record_success: Callable[[str], None],
    record_failure: Callable[[str, Exception], None],
    job_id: str = "collect_dividends",
) -> None:
    """KIS 배당 데이터 수집 — 보유 종목 단위로 일 1회 실행.

    KST 18:00 평일 (장 마감 + 정산 이후).
    """
    from app.services.kis_dividend import collect_dividends_for_user_holdings

    logger.info("[Scheduler] Starting dividend collection")
    try:
        async with AsyncSessionLocal() as db:
            acct_result = await db.execute(select(KisAccount).limit(1))
            acct = acct_result.scalar_one_or_none()
            if not acct:
                logger.info("[Scheduler] No KIS account found, skipping dividend collection")
                record_success(job_id)
                return

            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)
            stats = await collect_dividends_for_user_holdings(db, app_key, app_secret)

        logger.info("[Scheduler] Dividend collection results: %s", stats)
        if stats.get("errors", 0) == 0:
            record_success(job_id)
        else:
            # 일부 ticker 실패는 partial success로 간주 — 연속 실패 추적은
            # 전체 실패만 카운트해 noise를 줄인다.
            if stats.get("domestic", 0) + stats.get("overseas", 0) > 0:
                record_success(job_id)
            else:
                record_failure(
                    job_id,
                    RuntimeError(f"All dividend fetches failed: {stats}"),
                )

    except Exception as exc:
        record_failure(job_id, exc)
