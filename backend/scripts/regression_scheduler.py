"""Scheduler refactor regression check — no DB/Redis required.

Validates that the split-file delegation works end-to-end:
- All public symbols still importable from app.services.scheduler
- Wrapper functions delegate correctly and propagate record_success/failure
- start_scheduler registers 7 distinct job ids and calls scheduler.start()
- stop_scheduler calls scheduler.shutdown(wait=True)

Run directly: `python backend/scripts/regression_scheduler.py`
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("JWT_SECRET_KEY", "regression-check-dummy-secret-min-32-chars-long")
os.environ.setdefault("ENCRYPTION_MASTER_KEY", "a" * 64)  # 64-char hex placeholder
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _make_async_ctx(db: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def _empty_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    result.scalars.return_value = scalars
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    return db


async def test_sync_all_accounts_delegates() -> None:
    from app.services import scheduler as sched
    sched._consecutive_failures["kis_sync_us"] = 3

    db = _empty_db()
    with patch(
        "app.services.scheduler_portfolio_jobs.AsyncSessionLocal",
        return_value=_make_async_ctx(db),
    ):
        await sched._sync_all_accounts()

    # No accounts → success path → counter reset
    assert sched._consecutive_failures["kis_sync_us"] == 0, (
        f"expected 0, got {sched._consecutive_failures['kis_sync_us']}"
    )
    db.add.assert_not_called()
    print("  OK  _sync_all_accounts delegates to scheduler_portfolio_jobs")


async def test_sync_failure_increments_counter() -> None:
    from app.services import scheduler as sched
    sched._consecutive_failures["kis_sync_us"] = 0

    broken = MagicMock()
    broken.__aenter__ = AsyncMock(side_effect=RuntimeError("DB down"))
    broken.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.services.scheduler_portfolio_jobs.AsyncSessionLocal",
        return_value=broken,
    ):
        await sched._sync_all_accounts()

    assert sched._consecutive_failures["kis_sync_us"] == 1
    print("  OK  failure in split module increments scheduler counter")


async def test_snapshot_daily_close_delegates() -> None:
    from app.services import scheduler as sched
    sched._consecutive_failures["daily_close_snapshot"] = 2

    db = _empty_db()
    with patch(
        "app.services.scheduler_market_jobs.AsyncSessionLocal",
        return_value=_make_async_ctx(db),
    ):
        await sched._snapshot_daily_close()

    assert sched._consecutive_failures["daily_close_snapshot"] == 0
    print("  OK  _snapshot_daily_close delegates to scheduler_market_jobs")


async def test_preload_prices_chains_sync() -> None:
    from app.services import scheduler as sched
    sched._consecutive_failures["preload_prices_am"] = 0

    db = _empty_db()
    with (
        patch(
            "app.services.scheduler_portfolio_jobs.AsyncSessionLocal",
            return_value=_make_async_ctx(db),
        ),
        patch(
            "app.services.scheduler_market_jobs.AsyncSessionLocal",
            return_value=_make_async_ctx(db),
        ),
    ):
        await sched._preload_prices(job_id="preload_prices_am")

    assert sched._consecutive_failures["preload_prices_am"] == 0
    print("  OK  _preload_prices chains sync_all_accounts → preload")


async def test_other_wrappers_importable() -> None:
    from app.services.scheduler import (
        _collect_benchmark_snapshots,
        _save_fx_rate_snapshot,
        _settle_pending_orders,
    )
    assert callable(_collect_benchmark_snapshots)
    assert callable(_save_fx_rate_snapshot)
    assert callable(_settle_pending_orders)
    print("  OK  all wrapper functions importable")


def test_start_scheduler_registers_7_jobs() -> None:
    from app.services import scheduler as sched

    mock_scheduler = MagicMock()
    with (
        patch("app.services.scheduler.scheduler", mock_scheduler),
        patch.object(sched.logger, "info"),
    ):
        sched.start_scheduler()

    assert mock_scheduler.add_job.call_count == 7, (
        f"expected 7 jobs, got {mock_scheduler.add_job.call_count}"
    )
    job_ids = [c.kwargs.get("id") for c in mock_scheduler.add_job.call_args_list]
    expected = {
        "kis_sync_us", "daily_close_snapshot", "fx_rate_snapshot",
        "preload_prices_am", "preload_prices_pm",
        "settle_orders", "collect_benchmark",
    }
    assert set(job_ids) == expected, f"job ids mismatch: {job_ids}"
    assert mock_scheduler.start.called
    print("  OK  start_scheduler registers all 7 jobs with expected ids")


def test_stop_scheduler() -> None:
    from app.services import scheduler as sched

    mock_scheduler = MagicMock()
    with (
        patch("app.services.scheduler.scheduler", mock_scheduler),
        patch.object(sched.logger, "info"),
    ):
        sched.stop_scheduler()

    mock_scheduler.shutdown.assert_called_once_with(wait=True)
    print("  OK  stop_scheduler calls shutdown(wait=True)")


def test_consecutive_failure_threshold() -> None:
    from app.services import scheduler as sched

    sched._consecutive_failures["regression_test"] = 0
    for _ in range(sched.CONSECUTIVE_FAILURE_THRESHOLD):
        sched._record_job_failure("regression_test", RuntimeError("boom"))
    assert sched._consecutive_failures["regression_test"] == sched.CONSECUTIVE_FAILURE_THRESHOLD
    sched._record_job_success("regression_test")
    assert sched._consecutive_failures["regression_test"] == 0
    print("  OK  consecutive failure counter + critical threshold behavior")


async def main() -> int:
    print("Scheduler refactor regression checks")
    print("-" * 50)
    try:
        await test_sync_all_accounts_delegates()
        await test_sync_failure_increments_counter()
        await test_snapshot_daily_close_delegates()
        await test_preload_prices_chains_sync()
        await test_other_wrappers_importable()
        test_start_scheduler_registers_7_jobs()
        test_stop_scheduler()
        test_consecutive_failure_threshold()
    except AssertionError as exc:
        print(f"  FAIL  {exc}")
        return 1
    except Exception as exc:
        print(f"  ERROR {type(exc).__name__}: {exc}")
        return 2
    print("-" * 50)
    print("All regression checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
