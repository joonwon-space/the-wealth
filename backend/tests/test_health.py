"""GET /api/v1/health 엔드포인트 통합 테스트.

main.py의 health_check_v1 핸들러와 backup_health 서비스를 통해
상태 응답 및 백업 정보 필드를 검증한다.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

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
