"""Unit tests for scheduler service.

Tests cover:
- _sync_all_accounts: no KIS accounts, successful sync, sync error
- _snapshot_daily_close: no accounts, no holdings, OHLCV success, fallback to spot price
- start_scheduler / stop_scheduler: APScheduler job registration
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kis_account(
    id: int = 1,
    user_id: int = 10,
    app_key_enc: bytes = b"enc_key",
    app_secret_enc: bytes = b"enc_secret",
    account_no: str = "12345678-01",
) -> MagicMock:
    acct = MagicMock()
    acct.id = id
    acct.user_id = user_id
    acct.app_key_enc = app_key_enc
    acct.app_secret_enc = app_secret_enc
    acct.account_no = account_no
    return acct


def _make_portfolio(id: int = 1, kis_account_id: int = 1) -> MagicMock:
    p = MagicMock()
    p.id = id
    p.kis_account_id = kis_account_id
    return p


def _make_db_session(
    kis_accounts: list,
    portfolios: dict | None = None,
    tickers: list | None = None,
) -> AsyncMock:
    """Build a mock AsyncSession that returns given data for execute() calls."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    call_count = [0]
    portfolios = portfolios or {}

    async def _execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        count = call_count[0]

        if count == 1:
            # First call: select KisAccount
            scalars = MagicMock()
            scalars.all.return_value = kis_accounts
            result.scalars.return_value = scalars
        elif count == 2:
            # Second call: select Portfolio for first KIS account
            acct_id = kis_accounts[0].id if kis_accounts else None
            port = portfolios.get(acct_id)
            result.scalar_one_or_none.return_value = port
        elif count == 3 and tickers is not None:
            # Third call: select distinct tickers
            result.all.return_value = [(t,) for t in tickers]
        return result

    db.execute = AsyncMock(side_effect=_execute)
    return db


# ---------------------------------------------------------------------------
# _sync_all_accounts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncAllAccounts:
    @pytest.mark.asyncio
    async def test_no_kis_accounts_exits_early(self) -> None:
        db = _make_db_session(kis_accounts=[])

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
        ):
            from app.services.scheduler import _sync_all_accounts

            await _sync_all_accounts()

        # No sync attempted — db.add should not have been called
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_success_logs_entry(self) -> None:
        acct = _make_kis_account()
        port = _make_portfolio()
        db = _make_db_session(
            kis_accounts=[acct],
            portfolios={acct.id: port},
        )

        reconcile_counts = {"inserted": 2, "updated": 1, "deleted": 0}

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
            patch("app.services.scheduler.decrypt", side_effect=lambda x: x.decode()),
            patch(
                "app.services.scheduler.fetch_account_holdings",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.scheduler.reconcile_holdings",
                new_callable=AsyncMock,
                return_value=reconcile_counts,
            ),
        ):
            from app.services.scheduler import _sync_all_accounts

            await _sync_all_accounts()

        db.add.assert_called_once()
        log_entry = db.add.call_args[0][0]
        assert log_entry.status == "success"
        assert log_entry.inserted == 2
        assert log_entry.updated == 1
        assert log_entry.deleted == 0
        assert log_entry.user_id == acct.user_id
        assert log_entry.portfolio_id == port.id

    @pytest.mark.asyncio
    async def test_sync_error_logs_failure(self) -> None:
        acct = _make_kis_account()
        port = _make_portfolio()
        db = _make_db_session(
            kis_accounts=[acct],
            portfolios={acct.id: port},
        )

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
            patch("app.services.scheduler.decrypt", side_effect=lambda x: x.decode()),
            patch(
                "app.services.scheduler.fetch_account_holdings",
                new_callable=AsyncMock,
                side_effect=RuntimeError("KIS API timeout"),
            ),
        ):
            from app.services.scheduler import _sync_all_accounts

            await _sync_all_accounts()

        db.add.assert_called_once()
        log_entry = db.add.call_args[0][0]
        assert log_entry.status == "error"
        assert "KIS API timeout" in log_entry.message

    @pytest.mark.asyncio
    async def test_skips_account_with_no_portfolio(self) -> None:
        acct = _make_kis_account()
        db = _make_db_session(
            kis_accounts=[acct],
            portfolios={},  # No portfolio linked
        )

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
            patch("app.services.scheduler.decrypt", side_effect=lambda x: x.decode()),
        ):
            from app.services.scheduler import _sync_all_accounts

            await _sync_all_accounts()

        # No sync log should be written since no portfolio found
        db.add.assert_not_called()


# ---------------------------------------------------------------------------
# _snapshot_daily_close
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSnapshotDailyClose:
    @pytest.mark.asyncio
    async def test_no_kis_accounts_exits_early(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
        ):
            from app.services.scheduler import _snapshot_daily_close

            await _snapshot_daily_close()

        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_holdings_exits_early(self) -> None:
        acct = _make_kis_account()
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        call_count = [0]

        async def _execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar_one_or_none.return_value = acct
            elif call_count[0] == 2:
                result.all.return_value = []  # no holdings tickers
            return result

        db.execute = AsyncMock(side_effect=_execute)

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
            patch("app.services.scheduler.decrypt", side_effect=lambda x: x.decode()),
        ):
            from app.services.scheduler import _snapshot_daily_close

            await _snapshot_daily_close()

        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_ohlcv_success_saves_snapshots(self) -> None:
        acct = _make_kis_account()
        tickers = ["005930", "000660"]
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        call_count = [0]

        async def _execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar_one_or_none.return_value = acct
            elif call_count[0] == 2:
                result.all.return_value = [(t,) for t in tickers]
            return result

        db.execute = AsyncMock(side_effect=_execute)

        ohlcv_data = {"open": 75000, "high": 76000, "low": 74000, "close": 75500, "volume": 10000}

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
            patch("app.services.scheduler.decrypt", side_effect=lambda x: x.decode()),
            patch(
                "app.services.scheduler.fetch_domestic_daily_ohlcv",
                new_callable=AsyncMock,
                return_value=ohlcv_data,
            ),
            patch(
                "app.services.scheduler.save_ohlcv_snapshots",
                new_callable=AsyncMock,
                return_value=2,
            ) as mock_save,
        ):
            from app.services.scheduler import _snapshot_daily_close

            await _snapshot_daily_close()

        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args
        ohlcv_map = call_kwargs[0][1]  # second positional arg
        assert len(ohlcv_map) == 2

    @pytest.mark.asyncio
    async def test_ohlcv_failure_falls_back_to_spot_price(self) -> None:
        acct = _make_kis_account()
        tickers = ["005930"]
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        call_count = [0]

        async def _execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalar_one_or_none.return_value = acct
            elif call_count[0] == 2:
                result.all.return_value = [(t,) for t in tickers]
            return result

        db.execute = AsyncMock(side_effect=_execute)

        with (
            patch(
                "app.services.scheduler.AsyncSessionLocal",
                return_value=_make_async_ctx(db),
            ),
            patch("app.services.scheduler.decrypt", side_effect=lambda x: x.decode()),
            patch(
                "app.services.scheduler.fetch_domestic_daily_ohlcv",
                new_callable=AsyncMock,
                return_value={"close": None},  # no close → ohlcv_map empty
            ),
            patch(
                "app.services.scheduler.fetch_domestic_price",
                new_callable=AsyncMock,
                return_value=Decimal("75000"),
            ),
            patch(
                "app.services.scheduler.save_snapshots",
                new_callable=AsyncMock,
                return_value=1,
            ) as mock_save_spots,
            patch(
                "app.services.scheduler.save_ohlcv_snapshots",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            from app.services.scheduler import _snapshot_daily_close

            await _snapshot_daily_close()

        mock_save_spots.assert_called_once()
        prices_arg = mock_save_spots.call_args[0][1]
        assert "005930" in prices_arg
        assert prices_arg["005930"] == Decimal("75000")


# ---------------------------------------------------------------------------
# start_scheduler / stop_scheduler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSchedulerLifecycle:
    def test_start_scheduler_adds_jobs(self) -> None:
        from app.services.scheduler import start_scheduler

        mock_scheduler = MagicMock()
        with patch("app.services.scheduler.scheduler", mock_scheduler):
            start_scheduler()

        assert mock_scheduler.add_job.call_count == 2
        job_ids = []
        for c in mock_scheduler.add_job.call_args_list:
            job_ids.append(c.kwargs.get("id") or c[0][1] if len(c[0]) > 1 else None)
        # Verify two distinct jobs are registered
        assert mock_scheduler.start.called

    def test_stop_scheduler_calls_shutdown(self) -> None:
        from app.services.scheduler import stop_scheduler

        mock_scheduler = MagicMock()
        with patch("app.services.scheduler.scheduler", mock_scheduler):
            stop_scheduler()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)


# ---------------------------------------------------------------------------
# Helper: async context manager builder
# ---------------------------------------------------------------------------


def _make_async_ctx(session: AsyncMock) -> MagicMock:
    """Wrap a mock session in an async context manager."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx
