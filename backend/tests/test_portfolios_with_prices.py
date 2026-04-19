"""Tests for GET /portfolios/with-prices — unit (mocked KIS) + integration."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_login(client: AsyncClient, email: str) -> str:
    """Register a user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio(
    client: AsyncClient, token: str, name: str = "포트폴리오", currency: str = "KRW"
) -> int:
    resp = await client.post(
        "/portfolios", json={"name": name, "currency": currency}, headers=_auth(token)
    )
    return resp.json()["id"]


async def _add_holding(
    client: AsyncClient, token: str, pid: int, ticker: str, qty: float, avg: float,
    market: str | None = None
) -> None:
    body: dict = {
        "ticker": ticker, "name": ticker, "quantity": qty, "avg_price": avg
    }
    if market is not None:
        body["market"] = market
    await client.post(f"/portfolios/{pid}/holdings", json=body, headers=_auth(token))


# ---------------------------------------------------------------------------
# Unit tests — KIS calls are fully mocked
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPortfoliosWithPricesUnit:
    async def test_returns_price_fields_when_kis_available(
        self, client: AsyncClient
    ) -> None:
        """When KIS prices are available all P&L fields are populated."""
        token = await _register_login(client, "wp_unit1@test.com")
        pid = await _create_portfolio(client, token, "국내주식")
        await _add_holding(client, token, pid, "005930", 10, 70000)

        mock_price = Decimal("80000")
        mock_fx = Decimal("1450")

        with (
            patch(
                "app.api.portfolios.get_or_fetch_domestic_price",
                new_callable=AsyncMock,
                return_value=mock_price,
            ),
            patch(
                "app.api.portfolios.fetch_usd_krw_rate",
                new_callable=AsyncMock,
                return_value=mock_fx,
            ),
            patch("app.api.portfolios.decrypt", return_value="fake"),
        ):
            resp = await client.get("/portfolios/with-prices", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        row = data[0]
        assert row["id"] == pid
        # market_value_krw = 10 * 80000 = 800000
        assert row["market_value_krw"] is not None
        assert float(row["market_value_krw"]) == pytest.approx(800_000)
        # pnl_amount_krw = 800000 - 700000 = 100000
        assert row["pnl_amount_krw"] is not None
        assert float(row["pnl_amount_krw"]) == pytest.approx(100_000)
        # pnl_rate = 100000 / 700000 * 100 ≈ 14.285...
        assert row["pnl_rate"] is not None
        assert float(row["pnl_rate"]) == pytest.approx(100_000 / 700_000 * 100, rel=1e-3)

    async def test_price_fields_none_when_no_kis_account(
        self, client: AsyncClient
    ) -> None:
        """No KIS account linked → price fields are all None."""
        token = await _register_login(client, "wp_unit2@test.com")
        pid = await _create_portfolio(client, token, "KIS없음")
        await _add_holding(client, token, pid, "005930", 5, 60000)

        resp = await client.get("/portfolios/with-prices", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        row = data[0]
        assert row["market_value_krw"] is None
        assert row["pnl_amount_krw"] is None
        assert row["pnl_rate"] is None

    async def test_usd_portfolio_fx_converts_to_krw(
        self, client: AsyncClient
    ) -> None:
        """USD holdings market value and P&L are converted to KRW via exchange rate."""
        token = await _register_login(client, "wp_unit3@test.com")
        pid = await _create_portfolio(client, token, "US주식", "USD")
        # AAPL: 10 shares @ $150 avg, current price $200
        await _add_holding(client, token, pid, "AAPL", 10, 150, "NASD")

        mock_price = Decimal("200")
        mock_fx = Decimal("1400")

        with (
            patch(
                "app.api.portfolios.get_or_fetch_overseas_price",
                new_callable=AsyncMock,
                return_value=mock_price,
            ),
            patch(
                "app.api.portfolios.fetch_usd_krw_rate",
                new_callable=AsyncMock,
                return_value=mock_fx,
            ),
            patch("app.api.portfolios.decrypt", return_value="fake"),
        ):
            resp = await client.get("/portfolios/with-prices", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        row = data[0]
        # market_value_krw = 10 * 200 * 1400 = 2,800,000
        assert row["market_value_krw"] is not None
        assert float(row["market_value_krw"]) == pytest.approx(2_800_000)
        # invested_krw = 10 * 150 * 1400 = 2,100,000
        # pnl = 2,800,000 - 2,100,000 = 700,000
        assert float(row["pnl_amount_krw"]) == pytest.approx(700_000)
        # pnl_rate = 700,000 / 2,100,000 * 100 ≈ 33.33
        assert float(row["pnl_rate"]) == pytest.approx(700_000 / 2_100_000 * 100, rel=1e-3)

    async def test_deduplicates_tickers_across_portfolios(
        self, client: AsyncClient
    ) -> None:
        """Two portfolios sharing same ticker → KIS called once per unique ticker."""
        token = await _register_login(client, "wp_unit4@test.com")
        pid1 = await _create_portfolio(client, token, "포트A")
        pid2 = await _create_portfolio(client, token, "포트B")
        await _add_holding(client, token, pid1, "005930", 5, 70000)
        await _add_holding(client, token, pid2, "005930", 3, 72000)

        call_count = 0

        async def counting_price(ticker: str, app_key: str, app_secret: str, client) -> Decimal:  # type: ignore[override]
            nonlocal call_count
            call_count += 1
            return Decimal("75000")

        with (
            patch(
                "app.api.portfolios.get_or_fetch_domestic_price",
                side_effect=counting_price,
            ),
            patch("app.api.portfolios.decrypt", return_value="fake"),
        ):
            resp = await client.get("/portfolios/with-prices", headers=_auth(token))

        assert resp.status_code == 200
        # KIS price called exactly once for "005930" (deduplicated)
        assert call_count == 1


# ---------------------------------------------------------------------------
# Integration tests — no KIS mocking, verify API contract
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestPortfoliosWithPricesIntegration:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/portfolios/with-prices")
        assert resp.status_code in (401, 403)

    async def test_no_portfolios_returns_empty_list(self, client: AsyncClient) -> None:
        token = await _register_login(client, "wp_int2@test.com")
        resp = await client.get("/portfolios/with-prices", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_portfolio_without_kis_returns_null_prices(
        self, client: AsyncClient
    ) -> None:
        """KRW portfolio with holdings but no KIS account → price fields null."""
        token = await _register_login(client, "wp_int3@test.com")
        pid = await _create_portfolio(client, token, "국내주식")
        await _add_holding(client, token, pid, "005930", 10, 70000)

        resp = await client.get("/portfolios/with-prices", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        row = data[0]
        assert row["holdings_count"] == 1
        assert Decimal(row["total_invested"]) == Decimal("700000")
        # No KIS → price fields all None
        assert row["market_value_krw"] is None
        assert row["pnl_amount_krw"] is None
        assert row["pnl_rate"] is None

    async def test_response_schema_contains_base_fields(
        self, client: AsyncClient
    ) -> None:
        """Response includes all PortfolioResponse base fields."""
        token = await _register_login(client, "wp_int4@test.com")
        await _create_portfolio(client, token, "기본포트")

        resp = await client.get("/portfolios/with-prices", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        row = data[0]
        for field in ("id", "user_id", "name", "currency", "display_order",
                      "created_at", "holdings_count", "total_invested"):
            assert field in row, f"Missing base field: {field}"
