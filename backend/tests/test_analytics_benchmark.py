"""테스트 — 벤치마크 지수 API (GET /analytics/benchmark)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "benchmark_test@example.com"
) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestGetBenchmark:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/analytics/benchmark")
        assert resp.status_code in (401, 403)

    async def test_no_snapshots_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "bm_empty@example.com")
        resp = await client.get("/analytics/benchmark", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_invalid_index_code_returns_400(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "bm_invalid@example.com")
        resp = await client.get(
            "/analytics/benchmark",
            params={"index_code": "INVALID"},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    async def test_valid_index_code_kospi200(self, client: AsyncClient) -> None:
        """KOSPI200 스냅샷 데이터 조회."""
        import os
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.models.index_snapshot import IndexSnapshot

        token = await _register_and_get_token(client, "bm_kospi200@example.com")

        TEST_DB_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        _KST = timezone(timedelta(hours=9))
        async with factory() as db:
            base = datetime(2025, 1, 2, 16, 0, tzinfo=_KST)
            for i in range(3):
                db.add(IndexSnapshot(
                    index_code="KOSPI200",
                    timestamp=base + timedelta(days=i),
                    close_price=Decimal(2600 + i * 10),
                    change_pct=Decimal("0.5"),
                ))
            await db.commit()
        await engine.dispose()

        resp = await client.get(
            "/analytics/benchmark",
            params={"index_code": "KOSPI200"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Sorted by date
        dates = [item["date"] for item in data]
        assert dates == sorted(dates)
        # Fields check
        for item in data:
            assert "date" in item
            assert "close_price" in item
            assert isinstance(item["close_price"], (int, float))

    async def test_valid_index_code_sp500(self, client: AsyncClient) -> None:
        """SP500 스냅샷 데이터가 별도로 조회된다."""
        import os
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.models.index_snapshot import IndexSnapshot

        token = await _register_and_get_token(client, "bm_sp500@example.com")

        TEST_DB_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        _KST = timezone(timedelta(hours=9))
        async with factory() as db:
            ts = datetime(2025, 3, 10, 16, 0, tzinfo=_KST)
            db.add(IndexSnapshot(
                index_code="SP500",
                timestamp=ts,
                close_price=Decimal(5500.25),
                change_pct=Decimal("0.2"),
            ))
            await db.commit()
        await engine.dispose()

        resp = await client.get(
            "/analytics/benchmark",
            params={"index_code": "SP500"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert abs(data[0]["close_price"] - 5500.25) < 0.01

    async def test_from_filter_excludes_earlier_dates(self, client: AsyncClient) -> None:
        """from 파라미터: 해당 날짜 이전 스냅샷 제외."""
        import os
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.models.index_snapshot import IndexSnapshot

        token = await _register_and_get_token(client, "bm_from_filter@example.com")

        TEST_DB_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        _KST = timezone(timedelta(hours=9))
        async with factory() as db:
            for i in range(5):
                db.add(IndexSnapshot(
                    index_code="KOSPI200",
                    timestamp=datetime(2025, 6, i + 1, 16, 0, tzinfo=_KST),
                    close_price=Decimal(2700 + i * 5),
                    change_pct=Decimal("0.1"),
                ))
            await db.commit()
        await engine.dispose()

        resp = await client.get(
            "/analytics/benchmark",
            params={"index_code": "KOSPI200", "from": "2025-06-03"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            assert item["date"] >= "2025-06-03"

    async def test_default_index_code_is_kospi200(self, client: AsyncClient) -> None:
        """index_code 미지정 시 KOSPI200 기본값 사용 → 200 OK."""
        token = await _register_and_get_token(client, "bm_default@example.com")
        resp = await client.get("/analytics/benchmark", headers=_auth(token))
        assert resp.status_code == 200
