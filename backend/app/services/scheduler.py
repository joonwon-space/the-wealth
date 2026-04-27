"""APScheduler 기반 자동 동기화 스케줄러.

FastAPI 앱 startup/shutdown 이벤트에 연결하여 사용합니다.
Job 구현은 도메인별로 `scheduler_portfolio_jobs`, `scheduler_market_jobs`,
`scheduler_ops_jobs`에 분리되어 있으며, 이 모듈은 트리거 등록과 연속 실패
추적(`_consecutive_failures`)만 담당한다.
"""

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging import get_logger
from app.services.kis_health import check_kis_api_health, get_kis_availability
from app.services.scheduler_market_jobs import (
    collect_benchmark_snapshots,
    preload_prices,
    save_fx_rate_snapshot_job,
    snapshot_daily_close,
)
from app.services.scheduler_ops_jobs import settle_orders_job
from app.services.scheduler_portfolio_jobs import sync_all_accounts

logger = get_logger(__name__)

scheduler = AsyncIOScheduler()

CONSECUTIVE_FAILURE_THRESHOLD = 3

# KIS health re-check: track last re-check time when KIS is available
# to enforce 10-minute cooldown between proactive checks.
_KIS_HEALTH_RECHECK_COOLDOWN_SECONDS = 600  # 10 minutes
_last_healthy_check_at: datetime | None = None


async def _kis_health_recheck_job() -> None:
    """KIS API 가용성 주기적 재확인 잡.

    - is_available=False: 30초마다 즉시 재확인 → True 복귀 시 INFO 로그.
    - is_available=True: 10분 쿨다운 후 1회 확인해 부하 최소화.
    """
    global _last_healthy_check_at

    if not get_kis_availability():
        # KIS unreachable: run health check and attempt recovery
        recovered = await check_kis_api_health()
        if recovered:
            logger.info("[KisHealth] KIS API recovered — is_available=True")
            _last_healthy_check_at = datetime.now(timezone.utc)
        return

    # KIS is currently available: apply cooldown
    now = datetime.now(timezone.utc)
    if _last_healthy_check_at is not None:
        elapsed = (now - _last_healthy_check_at).total_seconds()
        if elapsed < _KIS_HEALTH_RECHECK_COOLDOWN_SECONDS:
            return  # Still in cooldown window

    # Cooldown elapsed or first run — run one proactive check
    await check_kis_api_health()
    _last_healthy_check_at = datetime.now(timezone.utc)


_consecutive_failures: dict[str, int] = {
    "kis_sync_us": 0,
    "daily_close_snapshot": 0,
    "fx_rate_snapshot": 0,
    "preload_prices_am": 0,
    "preload_prices_pm": 0,
    "settle_orders": 0,
    "collect_benchmark": 0,
}


def _record_job_success(job_id: str) -> None:
    """Reset consecutive failure counter on successful job execution."""
    _consecutive_failures[job_id] = 0


def _record_job_failure(job_id: str, exc: Exception) -> None:
    """Increment consecutive failure counter; emit CRITICAL log at threshold."""
    count = _consecutive_failures.get(job_id, 0) + 1
    _consecutive_failures[job_id] = count
    logger.warning(
        "[Scheduler] Job '%s' failed (consecutive=%d): %s", job_id, count, exc
    )
    if count >= CONSECUTIVE_FAILURE_THRESHOLD:
        logger.critical(
            "[Scheduler] ALERT: job '%s' has failed %d consecutive times. "
            "Immediate investigation required. Last error: %s",
            job_id,
            count,
            exc,
        )


async def _sync_all_accounts(job_id: str = "kis_sync_us") -> None:
    await sync_all_accounts(_record_job_success, _record_job_failure, job_id=job_id)


async def _snapshot_daily_close() -> None:
    await snapshot_daily_close(_record_job_success, _record_job_failure)


async def _preload_prices(job_id: str = "preload_prices") -> None:
    await preload_prices(
        _sync_all_accounts, _record_job_success, _record_job_failure, job_id=job_id
    )


async def _save_fx_rate_snapshot(job_id: str = "fx_rate_snapshot") -> None:
    await save_fx_rate_snapshot_job(
        _record_job_success, _record_job_failure, job_id=job_id
    )


async def _settle_pending_orders(job_id: str = "settle_orders") -> None:
    await settle_orders_job(_record_job_success, _record_job_failure, job_id=job_id)


async def _collect_benchmark_snapshots(job_id: str = "collect_benchmark") -> None:
    await collect_benchmark_snapshots(
        _record_job_success, _record_job_failure, job_id=job_id
    )


def start_scheduler() -> None:
    # 미국 장 마감 후 동기화: EST 16:00 ≈ UTC 21:30 (= KST 06:30)
    scheduler.add_job(
        _sync_all_accounts,
        trigger="cron", day_of_week="mon-fri", hour=21, minute=30, timezone="UTC",
        id="kis_sync_us", kwargs={"job_id": "kis_sync_us"}, replace_existing=True,
    )
    scheduler.add_job(
        _snapshot_daily_close,
        trigger="cron", day_of_week="mon-fri", hour=7, minute=10, timezone="UTC",
        id="daily_close_snapshot", replace_existing=True,
    )
    # 오전 홀딩 동기화 + 가격 캐시 워밍: KST 08:00 평일
    scheduler.add_job(
        _preload_prices,
        trigger="cron", day_of_week="mon-fri", hour=8, minute=0, timezone="Asia/Seoul",
        id="preload_prices_am", kwargs={"job_id": "preload_prices_am"}, replace_existing=True,
    )
    # 오후 홀딩 동기화 + 가격 캐시 워밍: KST 16:00 평일
    scheduler.add_job(
        _preload_prices,
        trigger="cron", day_of_week="mon-fri", hour=16, minute=0, timezone="Asia/Seoul",
        id="preload_prices_pm", kwargs={"job_id": "preload_prices_pm"}, replace_existing=True,
    )
    # 장 마감 후 환율 스냅샷: KST 16:30 평일
    scheduler.add_job(
        _save_fx_rate_snapshot,
        trigger="cron", day_of_week="mon-fri", hour=7, minute=30, timezone="UTC",
        id="fx_rate_snapshot", kwargs={"job_id": "fx_rate_snapshot"}, replace_existing=True,
    )
    # 미체결 주문 체결 확인: KST 09:05~15:35 평일 5분 간격
    scheduler.add_job(
        _settle_pending_orders,
        trigger="cron", day_of_week="mon-fri", hour="9-15", minute="*/5",
        timezone="Asia/Seoul",
        id="settle_orders", kwargs={"job_id": "settle_orders"}, replace_existing=True,
    )
    # 벤치마크 지수 스냅샷: KST 16:20 평일
    scheduler.add_job(
        _collect_benchmark_snapshots,
        trigger="cron", day_of_week="mon-fri", hour=7, minute=20, timezone="UTC",
        id="collect_benchmark", kwargs={"job_id": "collect_benchmark"}, replace_existing=True,
    )
    # KIS health re-check: 30초 간격 (is_available=False 시 즉시 복구 시도,
    # is_available=True 시 10분 쿨다운 후 1회 확인)
    scheduler.add_job(
        _kis_health_recheck_job,
        trigger="interval", seconds=30,
        id="kis_health_recheck", replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "[Scheduler] APScheduler started — "
        "holdings sync + price preload at KST 08:00 & 16:00, "
        "US close sync at KST 06:30, daily close snapshot at KST 16:10, "
        "FX snapshot at KST 16:30, benchmark snapshot at KST 16:20, "
        "order settlement every 5min during market hours, "
        "KIS health re-check every 30s"
    )


def stop_scheduler() -> None:
    scheduler.shutdown(wait=True)
    logger.info("[Scheduler] APScheduler stopped (waited for running jobs)")
