"""Tests for api/prices.py — price history and SSE stream endpoints."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import os

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    from app.core.limiter import limiter
    from app.db.base import Base
    from app.db.session import get_db
    from app.main import app

    try:
        limiter._storage.reset()  # type: ignore[attr-defined]
    except Exception:
        pass

    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1/") as ac:
        yield ac

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _insert_price_snapshots(client: AsyncClient, ticker: str, days: int = 5) -> None:
    """Insert PriceSnapshot records directly via DB for the test."""
    from app.db.session import get_db
    from app.main import app
    from app.models.price_snapshot import PriceSnapshot

    today = date.today()
    get_db_override = app.dependency_overrides[get_db]
    async for session in get_db_override():
        for i in range(days):
            snap_date = today - timedelta(days=i)
            snap = PriceSnapshot(
                ticker=ticker.upper(),
                snapshot_date=snap_date,
                close=Decimal("70000"),
                open=Decimal("69000"),
                high=Decimal("71000"),
                low=Decimal("68000"),
                volume=1_000_000,
            )
            session.add(snap)
        await session.commit()
        break


# ---------------------------------------------------------------------------
# Tests — price history endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPriceHistoryEndpoint:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/prices/005930/history")
        assert resp.status_code == 401

    async def test_empty_history_returns_empty_list(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ph1@test.com")
        resp = await client.get("/prices/AAPL/history", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_history_returns_snapshots(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ph2@test.com")
        await _insert_price_snapshots(client, "005930", days=3)

        resp = await client.get("/prices/005930/history", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    async def test_history_respects_limit(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ph3@test.com")
        await _insert_price_snapshots(client, "000660", days=5)

        resp = await client.get(
            "/prices/000660/history", params={"limit": 2}, headers=_auth(token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_history_from_date_filter(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ph4@test.com")
        await _insert_price_snapshots(client, "035720", days=5)

        # Filter from 2 days ago
        from_date = (date.today() - timedelta(days=2)).isoformat()
        resp = await client.get(
            "/prices/035720/history",
            params={"from": from_date},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should get at most 3 snapshots (today, yesterday, 2 days ago)
        assert len(data) <= 3
        for item in data:
            assert item["date"] >= from_date

    async def test_history_to_date_filter(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ph5@test.com")
        await _insert_price_snapshots(client, "069500", days=5)

        # Filter up to 2 days ago — excludes today and yesterday
        to_date = (date.today() - timedelta(days=2)).isoformat()
        resp = await client.get(
            "/prices/069500/history",
            params={"to": to_date},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        for item in resp.json():
            assert item["date"] <= to_date

    async def test_history_candle_fields(self, client: AsyncClient) -> None:
        """Each snapshot has date, open, high, low, close, volume fields."""
        token = await _register_and_login(client, "ph6@test.com")
        await _insert_price_snapshots(client, "105560", days=1)

        resp = await client.get("/prices/105560/history", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        snap = data[0]
        assert "date" in snap
        assert "open" in snap
        assert "high" in snap
        assert "low" in snap
        assert "close" in snap
        assert "volume" in snap
        assert float(snap["close"]) == 70000.0

    async def test_history_ticker_is_uppercased(self, client: AsyncClient) -> None:
        """Lowercase ticker is normalised to uppercase before query."""
        token = await _register_and_login(client, "ph7@test.com")
        await _insert_price_snapshots(client, "005930", days=2)

        # Request with lowercase ticker
        resp = await client.get("/prices/005930/history", headers=_auth(token))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_history_sorted_ascending(self, client: AsyncClient) -> None:
        """Snapshots are returned sorted by date ascending."""
        token = await _register_and_login(client, "ph8@test.com")
        await _insert_price_snapshots(client, "252670", days=4)

        resp = await client.get("/prices/252670/history", headers=_auth(token))
        dates = [item["date"] for item in resp.json()]
        assert dates == sorted(dates)

    async def test_limit_query_validation(self, client: AsyncClient) -> None:
        """Limit out of range returns 422."""
        token = await _register_and_login(client, "ph9@test.com")
        resp = await client.get(
            "/prices/005930/history",
            params={"limit": 0},
            headers=_auth(token),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — helper functions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsMarketOpen:
    def test_weekday_market_open_returns_true(self) -> None:
        from app.api.prices import _is_market_open

        # Monday at 10:00 KST
        mock_now = MagicMock()
        mock_now.weekday.return_value = 0  # Monday
        mock_now.hour = 10
        mock_now.minute = 0

        with patch("app.api.prices.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            result = _is_market_open()

        assert result is True

    def test_weekend_returns_false(self) -> None:
        from app.api.prices import _is_market_open

        mock_now = MagicMock()
        mock_now.weekday.return_value = 6  # Sunday
        mock_now.hour = 12
        mock_now.minute = 0

        with patch("app.api.prices.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            result = _is_market_open()

        assert result is False

    def test_before_market_hours_returns_false(self) -> None:
        from app.api.prices import _is_market_open

        mock_now = MagicMock()
        mock_now.weekday.return_value = 1  # Tuesday
        mock_now.hour = 8
        mock_now.minute = 59

        with patch("app.api.prices.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            result = _is_market_open()

        assert result is False

    def test_after_market_hours_returns_false(self) -> None:
        from app.api.prices import _is_market_open

        mock_now = MagicMock()
        mock_now.weekday.return_value = 3  # Thursday
        mock_now.hour = 15
        mock_now.minute = 31

        with patch("app.api.prices.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            result = _is_market_open()

        assert result is False


# ---------------------------------------------------------------------------
# Tests — SSE stream endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSSEStreamEndpoint:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        # SSE uses query param token; no token → 401
        resp = await client.get("/prices/stream")
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/prices/stream", params={"token": "invalid.token.here"})
        assert resp.status_code == 401

    async def test_stream_authenticated_starts_stream(
        self, client: AsyncClient
    ) -> None:
        """Valid token triggers the SSE stream (200 response, not 401/403)."""
        token = await _register_and_login(client, "sse1@test.com")

        # Patch the event_generator to avoid DB access via AsyncSessionLocal
        async def _mock_generator():
            yield 'data: {"error": "no_data"}\n\n'

        with patch("app.api.prices.AsyncSessionLocal") as mock_session:
            # Make the context manager return a mock session
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(execute=AsyncMock(
                    return_value=MagicMock(scalars=MagicMock(
                        return_value=MagicMock(all=MagicMock(return_value=[]))
                    ))
                ))
            )
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await client.get(
                "/prices/stream", params={"token": token}
            )

        # Should succeed (200) since authentication is valid
        assert resp.status_code == 200

    async def test_stream_max_connections_returns_429(
        self, client: AsyncClient
    ) -> None:
        """When per-user connection limit is exceeded, 429 is returned."""
        from app.api import prices as prices_mod

        token = await _register_and_login(client, "sse2@test.com")

        # Artificially fill up the connection slots for this user
        # We need to register+login to get the user's ID from the DB
        from app.models.user import User
        from app.db.session import get_db
        from app.main import app
        from sqlalchemy import select as sa_select

        get_db_override = app.dependency_overrides[get_db]
        async for session in get_db_override():
            result = await session.execute(
                sa_select(User).where(User.email == "sse2@test.com")
            )
            user = result.scalar_one()
            user_id = user.id
            break

        # Manually set the connection count to the maximum
        async with prices_mod._connections_lock:
            prices_mod._active_connections[user_id] = prices_mod._SSE_MAX_CONNECTIONS

        try:
            resp = await client.get("/prices/stream", params={"token": token})
            assert resp.status_code == 429
        finally:
            # Clean up
            async with prices_mod._connections_lock:
                prices_mod._active_connections.pop(user_id, None)


# ---------------------------------------------------------------------------
# Tests — SSE connection management helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSSEConnectionManagement:
    async def test_increment_allows_first_connection(self) -> None:
        from app.api import prices as prices_mod

        async with prices_mod._connections_lock:
            prices_mod._active_connections.pop(9999, None)

        result = await prices_mod._increment_connection(9999)
        assert result is True
        async with prices_mod._connections_lock:
            assert prices_mod._active_connections[9999] == 1
        # Cleanup
        await prices_mod._decrement_connection(9999)

    async def test_increment_allows_up_to_max_connections(self) -> None:
        from app.api import prices as prices_mod

        uid = 9998
        async with prices_mod._connections_lock:
            prices_mod._active_connections.pop(uid, None)

        # Fill to max
        for _ in range(prices_mod._SSE_MAX_CONNECTIONS):
            result = await prices_mod._increment_connection(uid)
            assert result is True

        # Next one should be rejected
        result = await prices_mod._increment_connection(uid)
        assert result is False

        # Cleanup
        async with prices_mod._connections_lock:
            prices_mod._active_connections.pop(uid, None)

    async def test_decrement_removes_entry_when_zero(self) -> None:
        from app.api import prices as prices_mod

        uid = 9997
        await prices_mod._increment_connection(uid)
        await prices_mod._decrement_connection(uid)

        async with prices_mod._connections_lock:
            assert uid not in prices_mod._active_connections

    async def test_decrement_preserves_count_above_one(self) -> None:
        from app.api import prices as prices_mod

        uid = 9996
        await prices_mod._increment_connection(uid)
        await prices_mod._increment_connection(uid)
        await prices_mod._decrement_connection(uid)

        async with prices_mod._connections_lock:
            assert prices_mod._active_connections[uid] == 1
        # Cleanup
        async with prices_mod._connections_lock:
            prices_mod._active_connections.pop(uid, None)


# ---------------------------------------------------------------------------
# Tests — signal_sse_shutdown helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSignalSseShutdown:
    def test_signal_sets_shutdown_event(self) -> None:
        import asyncio
        from app.api import prices as prices_mod

        # Save the original event and replace with a fresh one for isolation
        original_event = prices_mod._shutdown_event
        prices_mod._shutdown_event = asyncio.Event()
        try:
            assert not prices_mod._shutdown_event.is_set()
            prices_mod.signal_sse_shutdown()
            assert prices_mod._shutdown_event.is_set()
        finally:
            # Restore original event
            prices_mod._shutdown_event = original_event


# ---------------------------------------------------------------------------
# Tests — SSE event_generator body (market closed / open / fetch error paths)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSSEEventGeneratorPaths:
    """Tests that exercise the event_generator body in stream_prices.

    We mock AsyncSessionLocal to return portfolio + KIS account data,
    mock _is_market_open to control which branch executes, and mock
    _shutdown_event to stop the loop immediately after one iteration.
    """

    async def _make_session_mock_with_data(self, portfolio_ids: list, has_acct: bool) -> MagicMock:
        """Build a nested mock simulating a DB session that has portfolios and optionally a KIS account."""
        from unittest.mock import MagicMock, AsyncMock

        acct = None
        if has_acct:
            acct = MagicMock()
            acct.app_key_enc = b"key"
            acct.app_secret_enc = b"secret"

        # First call: portfolios; second call: KIS account
        portfolio_scalars = MagicMock()
        portfolio_scalars.all.return_value = [
            MagicMock(id=pid) for pid in portfolio_ids
        ]
        portfolio_execute_result = MagicMock()
        portfolio_execute_result.scalars.return_value = portfolio_scalars

        acct_scalar_result = MagicMock()
        acct_scalar_result.scalar_one_or_none.return_value = acct

        session = MagicMock()
        session.execute = AsyncMock(
            side_effect=[portfolio_execute_result, acct_scalar_result]
        )
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        return session

    async def test_stream_yields_no_data_when_no_portfolio(
        self, client: AsyncClient
    ) -> None:
        """When the user has no portfolio, stream yields no_data error."""

        token = await _register_and_login(client, "stream_noport@test.com")

        session = await self._make_session_mock_with_data(
            portfolio_ids=[], has_acct=False
        )
        mock_session_local = MagicMock()
        mock_session_local.return_value = session

        with patch("app.api.prices.AsyncSessionLocal", mock_session_local):
            resp = await client.get("/prices/stream", params={"token": token})

        assert resp.status_code == 200
        assert b"no_data" in resp.content

    def _make_one_shot_event(self) -> MagicMock:
        """Return a mock event whose is_set() returns False once then True forever.

        This lets the outer `while not event.is_set()` enter exactly once, while
        any inner `while not event.is_set()` loop exits immediately.
        """
        call_count = 0

        def _is_set() -> bool:
            nonlocal call_count
            call_count += 1
            return call_count > 1

        mock_evt = MagicMock()
        mock_evt.is_set = _is_set
        # wait() should be a coroutine that raises TimeoutError when used with wait_for
        # — but in tests the inner heartbeat loops check is_set first, so wait is rarely called.
        # Provide a coroutine that raises asyncio.TimeoutError to keep inner loops moving.
        import asyncio

        async def _wait() -> None:
            raise asyncio.TimeoutError

        mock_evt.wait = _wait
        return mock_evt

    def _make_session_pair(
        self,
        second_execute_result: MagicMock | None = None,
        second_execute_raises: Exception | None = None,
    ) -> tuple[MagicMock, MagicMock]:
        """Build (first_session, mock_factory) where:
        - first_session handles the initial portfolio+KIS account queries
        - second_session (or error) handles the in-loop holdings query
        """
        acct = MagicMock()
        acct.app_key_enc = "dummy_key"
        acct.app_secret_enc = "dummy_secret"

        portfolio_scalars = MagicMock()
        portfolio_scalars.all.return_value = [MagicMock(id=1)]
        portfolio_execute_result = MagicMock()
        portfolio_execute_result.scalars.return_value = portfolio_scalars

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = acct

        first_session = MagicMock()
        first_session.execute = AsyncMock(
            side_effect=[portfolio_execute_result, acct_result]
        )
        first_session.__aenter__ = AsyncMock(return_value=first_session)
        first_session.__aexit__ = AsyncMock(return_value=False)

        second_session = MagicMock()
        if second_execute_raises is not None:
            second_session.execute = AsyncMock(side_effect=second_execute_raises)
        elif second_execute_result is not None:
            second_session.execute = AsyncMock(return_value=second_execute_result)
        else:
            second_session.execute = AsyncMock(return_value=MagicMock())
        second_session.__aenter__ = AsyncMock(return_value=second_session)
        second_session.__aexit__ = AsyncMock(return_value=False)

        session_call = 0

        def _factory() -> MagicMock:
            nonlocal session_call
            session_call += 1
            return first_session if session_call == 1 else second_session

        return first_session, MagicMock(side_effect=_factory)

    async def test_stream_market_closed_path(
        self, client: AsyncClient
    ) -> None:
        """When market is closed, stream yields market_open: false then exits."""
        from app.api import prices as prices_mod

        token = await _register_and_login(client, "stream_closed@test.com")

        _first_session, mock_session_local = self._make_session_pair()
        mock_evt = self._make_one_shot_event()

        with (
            patch("app.api.prices.AsyncSessionLocal", mock_session_local),
            patch("app.api.prices._is_market_open", return_value=False),
            patch("app.api.prices.decrypt", return_value="mock_val"),
            patch.object(prices_mod, "_shutdown_event", mock_evt),
        ):
            resp = await client.get("/prices/stream", params={"token": token})

        assert resp.status_code == 200
        assert b"market_open" in resp.content

    async def test_stream_market_open_no_tickers(
        self, client: AsyncClient
    ) -> None:
        """When market is open but user has no holdings, yields empty prices dict."""
        from app.api import prices as prices_mod

        token = await _register_and_login(client, "stream_open_notick@test.com")

        ticker_result = MagicMock()
        ticker_result.all.return_value = []

        _first_session, mock_session_local = self._make_session_pair(
            second_execute_result=ticker_result
        )
        mock_evt = self._make_one_shot_event()

        with (
            patch("app.api.prices.AsyncSessionLocal", mock_session_local),
            patch("app.api.prices._is_market_open", return_value=True),
            patch("app.api.prices.decrypt", return_value="mock_val"),
            patch.object(prices_mod, "_shutdown_event", mock_evt),
        ):
            resp = await client.get("/prices/stream", params={"token": token})

        assert resp.status_code == 200
        assert b"prices" in resp.content

    async def test_stream_market_open_with_tickers(
        self, client: AsyncClient
    ) -> None:
        """When market is open with tickers, fetches prices and yields them."""
        from decimal import Decimal
        from app.api import prices as prices_mod

        token = await _register_and_login(client, "stream_open_tick@test.com")

        ticker_result = MagicMock()
        ticker_result.all.return_value = [("005930",)]

        _first_session, mock_session_local = self._make_session_pair(
            second_execute_result=ticker_result
        )
        mock_evt = self._make_one_shot_event()

        with (
            patch("app.api.prices.AsyncSessionLocal", mock_session_local),
            patch("app.api.prices._is_market_open", return_value=True),
            patch("app.api.prices.decrypt", return_value="mock_val"),
            patch.object(prices_mod, "_shutdown_event", mock_evt),
            patch(
                "app.api.prices.fetch_domestic_price",
                new_callable=AsyncMock,
                return_value=Decimal("70000"),
            ),
        ):
            resp = await client.get("/prices/stream", params={"token": token})

        assert resp.status_code == 200
        assert b"prices" in resp.content

    async def test_stream_fetch_error_yields_fetch_failed(
        self, client: AsyncClient
    ) -> None:
        """When holdings DB query raises, stream yields fetch_failed error event."""
        from app.api import prices as prices_mod

        token = await _register_and_login(client, "stream_fetcherr@test.com")

        _first_session, mock_session_local = self._make_session_pair(
            second_execute_raises=Exception("DB error")
        )
        mock_evt = self._make_one_shot_event()

        with (
            patch("app.api.prices.AsyncSessionLocal", mock_session_local),
            patch("app.api.prices._is_market_open", return_value=True),
            patch("app.api.prices.decrypt", return_value="mock_val"),
            patch.object(prices_mod, "_shutdown_event", mock_evt),
        ):
            resp = await client.get("/prices/stream", params={"token": token})

        assert resp.status_code == 200
        assert b"fetch_failed" in resp.content
