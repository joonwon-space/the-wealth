"""테스트 — SMA 이동평균 API (GET /analytics/stocks/{ticker}/sma)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "sma_test@example.com"
) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit tests for _compute_sma helper
# ---------------------------------------------------------------------------


class TestComputeSma:
    """_compute_sma 순수 함수 단위 테스트."""

    def test_single_element_returns_none_for_period_2(self) -> None:
        from app.api.analytics_sma import _compute_sma

        result = _compute_sma([100.0], period=2)
        assert result == [None]

    def test_exact_window_returns_value(self) -> None:
        from app.api.analytics_sma import _compute_sma

        result = _compute_sma([100.0, 200.0], period=2)
        assert result[0] is None
        assert result[1] == 150.0

    def test_period_1_returns_close_prices(self) -> None:
        """period=1 → SMA == close price."""
        from app.api.analytics_sma import _compute_sma

        closes = [50.0, 60.0, 70.0]
        result = _compute_sma(closes, period=1)
        assert result == [50.0, 60.0, 70.0]

    def test_5day_sma_correct(self) -> None:
        from app.api.analytics_sma import _compute_sma

        closes = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        result = _compute_sma(closes, period=5)
        # First 4 positions → None
        assert result[0] is None
        assert result[1] is None
        assert result[2] is None
        assert result[3] is None
        # 5th: mean of 10,20,30,40,50 = 30.0
        assert result[4] == 30.0
        # 6th: mean of 20,30,40,50,60 = 40.0
        assert result[5] == 40.0

    def test_empty_list_returns_empty(self) -> None:
        from app.api.analytics_sma import _compute_sma

        result = _compute_sma([], period=20)
        assert result == []

    def test_rounding_to_4_decimals(self) -> None:
        from app.api.analytics_sma import _compute_sma

        closes = [1.0, 2.0, 3.0]
        result = _compute_sma(closes, period=3)
        assert result[2] == round(2.0, 4)


# ---------------------------------------------------------------------------
# Integration tests — API endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGetStockSma:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/analytics/stocks/005930/sma")
        assert resp.status_code in (401, 403)

    async def test_no_snapshots_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "sma_nosnap@example.com")
        resp = await client.get("/analytics/stocks/005930/sma", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_insufficient_data_returns_empty(self, client: AsyncClient) -> None:
        """스냅샷이 period 미만이면 SMA 값 없음 → 빈 리스트."""
        from app.models.price_snapshot import PriceSnapshot
        import os
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        token = await _register_and_get_token(client, "sma_insufficient@example.com")

        TEST_DB_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            # Insert 5 snapshots; default period=20 → no valid SMA
            base = date(2024, 1, 2)
            for i in range(5):
                db.add(PriceSnapshot(
                    ticker="005930",
                    snapshot_date=base + timedelta(days=i),
                    close=Decimal(70000 + i * 100),
                ))
            await db.commit()
        await engine.dispose()

        resp = await client.get(
            "/analytics/stocks/005930/sma",
            params={"period": 20},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_with_enough_data_returns_sma_list(self, client: AsyncClient) -> None:
        """충분한 데이터가 있으면 SMA 리스트 반환."""
        from app.models.price_snapshot import PriceSnapshot
        import os
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        token = await _register_and_get_token(client, "sma_data@example.com")

        TEST_DB_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            base = date(2024, 1, 2)
            for i in range(5):
                db.add(PriceSnapshot(
                    ticker="AAPL",
                    snapshot_date=base + timedelta(days=i),
                    close=Decimal(100 + i * 10),  # 100,110,120,130,140
                ))
            await db.commit()
        await engine.dispose()

        resp = await client.get(
            "/analytics/stocks/AAPL/sma",
            params={"period": 3},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        # period=3, first valid SMA at index 2 (day 3)
        # SMA[2] = (100+110+120)/3 = 110.0
        # SMA[3] = (110+120+130)/3 = 120.0
        # SMA[4] = (120+130+140)/3 = 130.0
        assert len(data) == 3
        assert data[0]["sma"] == 110.0
        assert data[1]["sma"] == 120.0
        assert data[2]["sma"] == 130.0

    async def test_period_param_validation_min(self, client: AsyncClient) -> None:
        """period < 2 → 422 Validation error."""
        token = await _register_and_get_token(client, "sma_period_min@example.com")
        resp = await client.get(
            "/analytics/stocks/005930/sma",
            params={"period": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 422

    async def test_period_param_validation_max(self, client: AsyncClient) -> None:
        """period > 200 → 422 Validation error."""
        token = await _register_and_get_token(client, "sma_period_max@example.com")
        resp = await client.get(
            "/analytics/stocks/005930/sma",
            params={"period": 201},
            headers=_auth(token),
        )
        assert resp.status_code == 422

    async def test_from_filter_excludes_early_dates(self, client: AsyncClient) -> None:
        """from 파라미터로 from 이전 날짜가 응답에서 제외된다."""
        from app.models.price_snapshot import PriceSnapshot
        import os
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        token = await _register_and_get_token(client, "sma_from_filter@example.com")

        TEST_DB_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            base = date(2024, 1, 2)
            for i in range(6):
                db.add(PriceSnapshot(
                    ticker="MSFT",
                    snapshot_date=base + timedelta(days=i),
                    close=Decimal(300 + i * 5),
                ))
            await db.commit()
        await engine.dispose()

        # from=2024-01-05 이후만 응답에 포함되어야 함
        resp = await client.get(
            "/analytics/stocks/MSFT/sma",
            params={"period": 3, "from": "2024-01-05"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            assert item["date"] >= "2024-01-05"

    async def test_response_has_date_and_sma_fields(self, client: AsyncClient) -> None:
        """응답의 각 항목에 date, sma 필드가 있다."""
        from app.models.price_snapshot import PriceSnapshot
        import os
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        token = await _register_and_get_token(client, "sma_fields@example.com")

        TEST_DB_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            base = date(2024, 2, 1)
            for i in range(4):
                db.add(PriceSnapshot(
                    ticker="TSLA",
                    snapshot_date=base + timedelta(days=i),
                    close=Decimal(200 + i * 10),
                ))
            await db.commit()
        await engine.dispose()

        resp = await client.get(
            "/analytics/stocks/TSLA/sma",
            params={"period": 2},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for item in data:
            assert "date" in item
            assert "sma" in item
            assert isinstance(item["sma"], (int, float))
