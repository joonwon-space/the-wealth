"""GET /api/v1/health 엔드포인트 통합 테스트.

main.py의 health_check_v1 핸들러와 backup_health 서비스를 통해
상태 응답 및 백업 정보 필드를 검증한다.

또한 /health/data-integrity, /health/holdings-reconciliation,
/health/orphan-records 라우터 엔드포인트를 통합 테스트한다.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import os

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)


@pytest_asyncio.fixture
async def health_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client bound to /api/v1 base URL."""
    from app.db.session import get_db
    from app.main import app
    from tests.conftest import _clean_all_data

    await _clean_all_data()

    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1/") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.integration
class TestHealthCheckV1:
    async def test_returns_status_ok(self, health_client: AsyncClient) -> None:
        """GET /api/v1/health 는 status: ok 를 반환해야 한다."""
        with patch(
            "app.main.get_last_backup_info",
            new_callable=AsyncMock,
            return_value={"last_backup_at": None, "backup_age_hours": None},
        ):
            resp = await health_client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_response_contains_backup_fields(
        self, health_client: AsyncClient
    ) -> None:
        """응답에 last_backup_at, backup_age_hours 필드가 포함되어야 한다."""
        with patch(
            "app.main.get_last_backup_info",
            new_callable=AsyncMock,
            return_value={"last_backup_at": None, "backup_age_hours": None},
        ):
            resp = await health_client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "last_backup_at" in data
        assert "backup_age_hours" in data

    async def test_backup_info_null_when_no_backup(
        self, health_client: AsyncClient
    ) -> None:
        """백업 파일이 없을 때 last_backup_at과 backup_age_hours 는 null이어야 한다."""
        with patch(
            "app.main.get_last_backup_info",
            new_callable=AsyncMock,
            return_value={"last_backup_at": None, "backup_age_hours": None},
        ):
            resp = await health_client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["last_backup_at"] is None
        assert data["backup_age_hours"] is None

    async def test_backup_info_populated_when_backup_exists(
        self, health_client: AsyncClient
    ) -> None:
        """백업이 존재할 때 last_backup_at과 backup_age_hours 가 채워져야 한다."""
        fake_ts = "2026-03-20T02:00:00+00:00"
        with patch(
            "app.main.get_last_backup_info",
            new_callable=AsyncMock,
            return_value={"last_backup_at": fake_ts, "backup_age_hours": 7.5},
        ):
            resp = await health_client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["last_backup_at"] == fake_ts
        assert data["backup_age_hours"] == 7.5

    async def test_does_not_require_authentication(
        self, health_client: AsyncClient
    ) -> None:
        """헬스체크는 인증 없이 접근 가능해야 한다."""
        with patch(
            "app.main.get_last_backup_info",
            new_callable=AsyncMock,
            return_value={"last_backup_at": None, "backup_age_hours": None},
        ):
            resp = await health_client.get("/health")

        assert resp.status_code == 200


# ─── /health/data-integrity 테스트 ───────────────────────────────────────────


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


@pytest.mark.integration
class TestDataIntegrity:
    async def test_returns_degraded_when_no_snapshots(self, client: AsyncClient) -> None:
        """스냅샷이 없으면 missing_snapshots에 날짜가 채워지고 status=degraded."""
        token = await _register_login(client, "di_nosnap@test.com")
        resp = await client.get(
            "/health/data-integrity",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "missing_snapshots" in data
        assert "present_snapshots" in data
        assert "checked_weekdays" in data
        # 스냅샷 없으므로 degraded
        assert data["status"] == "degraded"
        assert len(data["missing_snapshots"]) > 0

    async def test_data_integrity_requires_authentication(
        self, client: AsyncClient
    ) -> None:
        """인증 없이 접근 시 401 반환."""
        resp = await client.get("/health/data-integrity")
        assert resp.status_code == 401

    async def test_returns_present_snapshots_when_exist(
        self, client: AsyncClient
    ) -> None:
        """최근 평일 스냅샷이 존재할 때 present_snapshots에 포함."""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy.pool import NullPool
        from app.models.price_snapshot import PriceSnapshot

        token = await _register_login(client, "di_snap@test.com")

        # 가장 최근 평일 찾기
        today = date.today()
        test_date = today
        while test_date.weekday() >= 5:
            test_date -= timedelta(days=1)

        db_url = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
        )
        engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            session.add(PriceSnapshot(
                ticker="005930",
                snapshot_date=test_date,
                close=70000,
            ))
            await session.commit()
        await engine.dispose()

        resp = await client.get(
            "/health/data-integrity",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert test_date.isoformat() in data["present_snapshots"]


# ─── /health/holdings-reconciliation 테스트 ──────────────────────────────────


@pytest.mark.integration
class TestHoldingsReconciliation:
    async def test_no_portfolios_returns_ok(self, client: AsyncClient) -> None:
        """포트폴리오가 없으면 checked_holdings=0, status=ok."""
        token = await _register_login(client, "recon_empty@test.com")
        resp = await client.get(
            "/health/holdings-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["checked_holdings"] == 0
        assert data["mismatches"] == []

    async def test_reconciliation_requires_authentication(
        self, client: AsyncClient
    ) -> None:
        """인증 없이 접근 시 401 반환."""
        resp = await client.get("/health/holdings-reconciliation")
        assert resp.status_code == 401

    async def test_matching_holdings_ok(self, client: AsyncClient) -> None:
        """보유수량과 거래내역이 일치하면 status=ok."""
        token = await _register_login(client, "recon_match@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        port_resp = await client.post(
            "/portfolios", json={"name": "Test"}, headers=headers
        )
        port_id = port_resp.json()["id"]
        await client.post(
            f"/portfolios/{port_id}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": "5", "avg_price": "70000"},
            headers=headers,
        )
        # 매수 거래 추가
        await client.post(
            f"/portfolios/{port_id}/transactions",
            json={
                "ticker": "005930",
                "type": "BUY",
                "quantity": "5",
                "price": "70000",
                "traded_at": "2026-01-01T00:00:00",
            },
            headers=headers,
        )

        resp = await client.get(
            "/health/holdings-reconciliation", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["checked_holdings"] == 1
        assert data["mismatches"] == []

    async def test_mismatched_holdings_degraded(self, client: AsyncClient) -> None:
        """보유수량과 거래내역이 불일치하면 status=degraded, mismatches 반환."""
        token = await _register_login(client, "recon_mismatch@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        port_resp = await client.post(
            "/portfolios", json={"name": "Test"}, headers=headers
        )
        port_id = port_resp.json()["id"]
        # holdings: 10주, transactions: 5주만 기록
        await client.post(
            f"/portfolios/{port_id}/holdings",
            json={"ticker": "035720", "name": "카카오", "quantity": "10", "avg_price": "50000"},
            headers=headers,
        )
        await client.post(
            f"/portfolios/{port_id}/transactions",
            json={
                "ticker": "035720",
                "type": "BUY",
                "quantity": "5",
                "price": "50000",
                "traded_at": "2026-01-01T00:00:00",
            },
            headers=headers,
        )

        resp = await client.get(
            "/health/holdings-reconciliation", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert len(data["mismatches"]) == 1
        assert data["mismatches"][0]["ticker"] == "035720"


# ─── /health/orphan-records 테스트 ───────────────────────────────────────────


@pytest.mark.integration
class TestOrphanRecords:
    async def test_no_portfolios_returns_ok(self, client: AsyncClient) -> None:
        """포트폴리오가 없으면 모두 0, status=ok."""
        token = await _register_login(client, "orphan_empty@test.com")
        resp = await client.get(
            "/health/orphan-records",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["orphan_holdings"] == 0
        assert data["orphan_transactions"] == 0
        assert data["orphan_sync_logs"] == 0

    async def test_orphan_requires_authentication(
        self, client: AsyncClient
    ) -> None:
        """인증 없이 접근 시 401 반환."""
        resp = await client.get("/health/orphan-records")
        assert resp.status_code == 401

    async def test_clean_data_returns_ok(self, client: AsyncClient) -> None:
        """정상 데이터는 고아 레코드 없이 ok 반환."""
        token = await _register_login(client, "orphan_clean@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        port_resp = await client.post(
            "/portfolios", json={"name": "Clean"}, headers=headers
        )
        port_id = port_resp.json()["id"]
        await client.post(
            f"/portfolios/{port_id}/holdings",
            json={
                "ticker": "000660",
                "name": "SK하이닉스",
                "quantity": "3",
                "avg_price": "180000",
            },
            headers=headers,
        )

        resp = await client.get("/health/orphan-records", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["orphan_holdings"] == 0
