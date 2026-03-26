"""통합 테스트 — analytics API endpoints."""

import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)


@asynccontextmanager
async def _db_session():
    """Direct DB session using the shared test DB (tables already created by client fixture)."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _register_and_get_token(
    client: AsyncClient, email: str = "analytics@example.com"
) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _setup_portfolio_with_holdings(
    client: AsyncClient, token: str, holdings: list[dict]
) -> int:
    port = (
        await client.post("/portfolios", json={"name": "분석 테스트"}, headers=_auth(token))
    ).json()
    pid = port["id"]
    for h in holdings:
        await client.post(f"/portfolios/{pid}/holdings", json=h, headers=_auth(token))
    return pid


@pytest.mark.integration
class TestGetMetricsEmpty:
    async def test_no_portfolios_returns_null_metrics(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "metrics_empty1@example.com")
        resp = await client.get("/analytics/metrics", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_return_rate"] is None
        assert data["cagr"] is None
        assert data["mdd"] is None
        assert data["sharpe_ratio"] is None

    async def test_no_holdings_returns_null_metrics(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "metrics_empty2@example.com")
        await client.post("/portfolios", json={"name": "빈 포트폴리오"}, headers=_auth(token))
        resp = await client.get("/analytics/metrics", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_return_rate"] is None
        assert data["cagr"] is None

    async def test_metrics_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/analytics/metrics")
        assert resp.status_code in (401, 403)

    @patch("app.api.analytics.fetch_domestic_price_detail", new_callable=AsyncMock)
    async def test_metrics_no_snapshots_uses_avg_price(
        self, mock_fetch: AsyncMock, client: AsyncClient
    ) -> None:
        """No snapshots → total_return_rate is 0 (current price falls back to avg_price)."""
        token = await _register_and_get_token(client, "metrics_nosnap@example.com")
        # No KIS account → won't call fetch; no snapshots → uses avg_price as current price
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )
        resp = await client.get("/analytics/metrics", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        # No KIS account, no snapshots → current price == avg_price → 0% return
        assert data["total_return_rate"] == 0.0
        assert data["mdd"] == 0.0
        assert data["cagr"] is None  # no portfolio_values list
        assert data["sharpe_ratio"] is None  # no daily returns


@pytest.mark.integration
class TestGetPortfolioHistory:
    async def test_no_portfolios_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "history_empty1@example.com")
        resp = await client.get("/analytics/portfolio-history", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_no_holdings_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "history_empty2@example.com")
        await client.post("/portfolios", json={"name": "빈"}, headers=_auth(token))
        resp = await client.get("/analytics/portfolio-history", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_no_snapshots_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "history_nosnap@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )
        resp = await client.get("/analytics/portfolio-history", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_with_snapshots_returns_history(self, client: AsyncClient) -> None:
        """With price_snapshots inserted, portfolio-history returns daily values."""
        from app.models.price_snapshot import PriceSnapshot

        token = await _register_and_get_token(client, "history_data@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )

        async with _db_session() as db:
            base_date = date(2024, 1, 2)
            for i in range(3):
                snap = PriceSnapshot(
                    ticker="005930",
                    snapshot_date=base_date + timedelta(days=i),
                    close=Decimal(70000 + i * 1000),
                )
                db.add(snap)
            await db.commit()

        resp = await client.get("/analytics/portfolio-history", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # First day: 10 shares × 70000 = 700000
        assert data[0]["value"] == 700000.0
        assert data[1]["value"] == 710000.0
        assert data[2]["value"] == 720000.0

    async def test_portfolio_history_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/analytics/portfolio-history")
        assert resp.status_code in (401, 403)

    async def test_period_filter_1m(self, client: AsyncClient) -> None:
        """period=1M filters snapshots to last 30 days only."""
        from app.models.price_snapshot import PriceSnapshot

        token = await _register_and_get_token(client, "history_period1m@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )

        today = date.today()
        async with _db_session() as db:
            # One snapshot 2 years ago (should be filtered out)
            old_snap = PriceSnapshot(
                ticker="005930",
                snapshot_date=today - timedelta(days=730),
                close=Decimal("60000"),
            )
            # One snapshot 10 days ago (should be included)
            recent_snap = PriceSnapshot(
                ticker="005930",
                snapshot_date=today - timedelta(days=10),
                close=Decimal("75000"),
            )
            db.add(old_snap)
            db.add(recent_snap)
            await db.commit()

        resp = await client.get(
            "/analytics/portfolio-history", params={"period": "1M"}, headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only the recent snapshot within 30 days
        assert len(data) == 1
        assert data[0]["value"] == 750000.0

    async def test_period_all_returns_all_snapshots(self, client: AsyncClient) -> None:
        """period=ALL returns all available snapshots."""
        from app.models.price_snapshot import PriceSnapshot

        token = await _register_and_get_token(client, "history_period_all@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )

        today = date.today()
        async with _db_session() as db:
            for delta in (365, 10):
                snap = PriceSnapshot(
                    ticker="005930",
                    snapshot_date=today - timedelta(days=delta),
                    close=Decimal("70000"),
                )
                db.add(snap)
            await db.commit()

        resp = await client.get(
            "/analytics/portfolio-history", params={"period": "ALL"}, headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    async def test_period_filter_1w(self, client: AsyncClient) -> None:
        """period=1W filters snapshots to last 7 days only."""
        from app.models.price_snapshot import PriceSnapshot

        token = await _register_and_get_token(client, "history_period1w@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 5, "avg_price": 70000}],
        )

        today = date.today()
        async with _db_session() as db:
            # Snapshot 30 days ago — should be excluded by 1W filter
            old_snap = PriceSnapshot(
                ticker="005930",
                snapshot_date=today - timedelta(days=30),
                close=Decimal("65000"),
            )
            # Snapshot 3 days ago — should be included
            recent_snap = PriceSnapshot(
                ticker="005930",
                snapshot_date=today - timedelta(days=3),
                close=Decimal("72000"),
            )
            db.add(old_snap)
            db.add(recent_snap)
            await db.commit()

        resp = await client.get(
            "/analytics/portfolio-history", params={"period": "1W"}, headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only the recent snapshot within 7 days
        assert len(data) == 1
        assert data[0]["value"] == 360000.0  # 5 * 72000


@pytest.mark.integration
class TestGetMonthlyReturns:
    async def test_no_portfolios_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "monthly_empty1@example.com")
        resp = await client.get("/analytics/monthly-returns", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_no_holdings_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "monthly_empty2@example.com")
        await client.post("/portfolios", json={"name": "빈"}, headers=_auth(token))
        resp = await client.get("/analytics/monthly-returns", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_no_snapshots_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "monthly_nosnap@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )
        resp = await client.get("/analytics/monthly-returns", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_single_month_returns_empty(self, client: AsyncClient) -> None:
        """Only one month of snapshots → no month-over-month return possible."""
        from app.models.price_snapshot import PriceSnapshot

        token = await _register_and_get_token(client, "monthly_oneMonth@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )

        async with _db_session() as db:
            for day in [1, 15, 28]:
                db.add(PriceSnapshot(
                    ticker="005930",
                    snapshot_date=date(2024, 1, day),
                    close=Decimal(70000),
                ))
            await db.commit()

        resp = await client.get("/analytics/monthly-returns", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_two_months_returns_one_entry(self, client: AsyncClient) -> None:
        """Two months of snapshots → one monthly return entry."""
        from app.models.price_snapshot import PriceSnapshot

        token = await _register_and_get_token(client, "monthly_twoMonth@example.com")
        await _setup_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )

        async with _db_session() as db:
            # Jan end: 70000, Feb end: 77000 → +10%
            db.add(PriceSnapshot(ticker="005930", snapshot_date=date(2024, 1, 31), close=Decimal(70000)))
            db.add(PriceSnapshot(ticker="005930", snapshot_date=date(2024, 2, 29), close=Decimal(77000)))
            await db.commit()

        resp = await client.get("/analytics/monthly-returns", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["year"] == 2024
        assert data[0]["month"] == 2
        # 10 shares × 77000 = 770000; prev = 10 × 70000 = 700000; return = 10.0%
        assert data[0]["return_rate"] == 10.0

    async def test_monthly_returns_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/analytics/monthly-returns")
        assert resp.status_code in (401, 403)
