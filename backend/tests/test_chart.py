"""Tests for api/chart.py — daily OHLCV chart data endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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
# Shared fixture
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


async def _register_and_login(client: AsyncClient, email: str = "chartuser@test.com") -> str:
    """Register + login; return Bearer token."""
    await client.post(
        "/auth/register",
        json={"email": email, "password": "TestPass123!"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    return resp.json()["access_token"]


async def _add_kis_account(client: AsyncClient, token: str) -> None:
    """Add a KIS account for the current user via API."""
    await client.post(
        "/users/kis-accounts",
        json={
            "label": "Test",
            "account_no": "12345678",
            "acnt_prdt_cd": "01",
            "app_key": "dummy_key",
            "app_secret": "dummy_secret",
        },
        headers={"Authorization": f"Bearer {token}"},
    )


def _make_kis_resp(items: list[dict]) -> MagicMock:
    """Build a mock httpx.Response that returns *items* in the KIS shape."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"output2": items}
    return mock_resp


def _ohlcv_item(date_str: str) -> dict:
    return {
        "stck_bsop_date": date_str,
        "stck_oprc": "70000",
        "stck_hgpr": "72000",
        "stck_lwpr": "69000",
        "stck_clpr": "71000",
        "acml_vol": "1000000",
    }


def _make_mock_httpx_client(items: list[dict]) -> MagicMock:
    """Return a mock context manager that wraps a mock httpx.AsyncClient."""
    mock_resp = _make_kis_resp(items)
    mock_aclient = AsyncMock(spec=httpx.AsyncClient)
    mock_aclient.get = AsyncMock(return_value=mock_resp)
    # Make it work as an async context manager
    mock_aclient.__aenter__ = AsyncMock(return_value=mock_aclient)
    mock_aclient.__aexit__ = AsyncMock(return_value=False)
    return mock_aclient


def _make_error_mock_httpx_client() -> MagicMock:
    """Return a mock context manager whose .get raises HTTPStatusError."""
    http_error = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )
    mock_aclient = AsyncMock(spec=httpx.AsyncClient)
    mock_aclient.get = AsyncMock(side_effect=http_error)
    mock_aclient.__aenter__ = AsyncMock(return_value=mock_aclient)
    mock_aclient.__aexit__ = AsyncMock(return_value=False)
    return mock_aclient


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDailyChartEndpoint:
    async def test_no_kis_account_returns_400(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.get(
            "/chart/daily",
            params={"ticker": "005930"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        body = resp.json()
        # Error format: {"error": {"code": ..., "message": ...}}
        error_msg = body.get("detail") or body.get("error", {}).get("message", "")
        assert "KIS" in error_msg

    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/chart/daily", params={"ticker": "005930"})
        assert resp.status_code == 401

    async def test_invalid_period_returns_422(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "chartuser2@test.com")
        resp = await client.get(
            "/chart/daily",
            params={"ticker": "005930", "period": "10Y"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_missing_ticker_returns_422(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "chartuser3@test.com")
        resp = await client.get(
            "/chart/daily",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_returns_candles_with_kis_account(self, client: AsyncClient) -> None:
        """With a KIS account and mocked KIS API, daily candles are returned."""
        token = await _register_and_login(client, "chartuser4@test.com")
        await _add_kis_account(client, token)

        items = [
            _ohlcv_item("20240102"),
            _ohlcv_item("20240103"),
            _ohlcv_item("20240104"),
        ]
        mock_client = _make_mock_httpx_client(items)

        with (
            patch("app.api.chart.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.chart.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get(
                "/chart/daily",
                params={"ticker": "005930", "period": "3M"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["period"] == "3M"
        assert isinstance(data["candles"], list)

    async def test_kis_api_error_returns_502(self, client: AsyncClient) -> None:
        """KIS HTTP error is converted to 502 Bad Gateway."""
        token = await _register_and_login(client, "chartuser5@test.com")
        await _add_kis_account(client, token)

        mock_client = _make_error_mock_httpx_client()

        with (
            patch("app.api.chart.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.chart.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get(
                "/chart/daily",
                params={"ticker": "005930"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 502

    async def test_candles_sorted_ascending_and_deduped(self, client: AsyncClient) -> None:
        """Candles are sorted ascending by date and duplicates removed."""
        token = await _register_and_login(client, "chartuser6@test.com")
        await _add_kis_account(client, token)

        # KIS returns newest-first; include a duplicate
        items = [
            _ohlcv_item("20240104"),
            _ohlcv_item("20240103"),
            _ohlcv_item("20240103"),  # duplicate
            _ohlcv_item("20240102"),
        ]
        mock_client = _make_mock_httpx_client(items)

        with (
            patch("app.api.chart.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.chart.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get(
                "/chart/daily",
                params={"ticker": "005930", "period": "3M"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        candles = resp.json()["candles"]
        dates = [c["time"] for c in candles]
        assert dates == sorted(set(dates)), "candles must be sorted ascending without duplicates"

    async def test_candle_fields_are_present(self, client: AsyncClient) -> None:
        """Each candle contains time, open, high, low, close, volume."""
        from datetime import date, timedelta

        token = await _register_and_login(client, "chartuser7@test.com")
        await _add_kis_account(client, token)

        # Use a date within the last 30 days so the chart filter doesn't drop it
        recent = date.today() - timedelta(days=5)
        date_str = recent.strftime("%Y%m%d")
        expected_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        items = [_ohlcv_item(date_str)]
        mock_client = _make_mock_httpx_client(items)

        with (
            patch("app.api.chart.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.chart.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get(
                "/chart/daily",
                params={"ticker": "005930", "period": "1M"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        candles = resp.json()["candles"]
        assert len(candles) == 1
        c = candles[0]
        assert c["time"] == expected_time
        assert c["open"] == 70000.0
        assert c["high"] == 72000.0
        assert c["low"] == 69000.0
        assert c["close"] == 71000.0
        assert c["volume"] == 1000000

    async def test_empty_kis_response_returns_empty_candles(self, client: AsyncClient) -> None:
        """No items from KIS → empty candles list, not an error."""
        token = await _register_and_login(client, "chartuser8@test.com")
        await _add_kis_account(client, token)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {}  # no output key

        mock_aclient = AsyncMock(spec=httpx.AsyncClient)
        mock_aclient.get = AsyncMock(return_value=mock_resp)
        mock_aclient.__aenter__ = AsyncMock(return_value=mock_aclient)
        mock_aclient.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.api.chart.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.chart.httpx.AsyncClient", return_value=mock_aclient),
        ):
            resp = await client.get(
                "/chart/daily",
                params={"ticker": "005930", "period": "1M"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["candles"] == []

    async def test_all_valid_period_codes_accepted(self, client: AsyncClient) -> None:
        """All defined period codes (1M, 3M, 6M, 1Y, 3Y) pass validation."""
        token = await _register_and_login(client, "chartuser9@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Without a KIS account they all return 400, not 422
        for period in ("1M", "3M", "6M", "1Y", "3Y"):
            resp = await client.get(
                "/chart/daily",
                params={"ticker": "005930", "period": period},
                headers=headers,
            )
            assert resp.status_code == 400, (
                f"period={period} should fail with 400 (no KIS account), got {resp.status_code}"
            )
