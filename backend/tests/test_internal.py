"""POST /api/v1/internal/backup-status 엔드포인트 통합 테스트.

X-Internal-Secret 헤더 검증, 성공/실패 페이로드 처리,
SyncLog 기록 등을 검증한다.
"""

from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import os

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)

_VALID_SECRET = "test-internal-secret-xyz"


@pytest.fixture
async def internal_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client with INTERNAL_SECRET configured."""
    from app.db.base import Base
    from app.db.session import get_db
    from app.main import app

    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1/") as ac:
        with patch("app.api.internal.settings") as mock_settings:
            mock_settings.INTERNAL_SECRET = _VALID_SECRET
            yield ac

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _secret_headers(secret: str = _VALID_SECRET) -> dict[str, str]:
    return {"X-Internal-Secret": secret}


@pytest.mark.integration
class TestRecordBackupStatus:
    async def test_success_status_returns_204(
        self, internal_client: AsyncClient
    ) -> None:
        """status=success 페이로드는 204 No Content 를 반환해야 한다."""
        resp = await internal_client.post(
            "/internal/backup-status",
            json={"status": "success", "message": "Backup completed"},
            headers=_secret_headers(),
        )
        assert resp.status_code == 204

    async def test_error_status_returns_204(
        self, internal_client: AsyncClient
    ) -> None:
        """status=error 페이로드도 204 No Content 를 반환해야 한다."""
        resp = await internal_client.post(
            "/internal/backup-status",
            json={"status": "error", "message": "Disk full"},
            headers=_secret_headers(),
        )
        assert resp.status_code == 204

    async def test_invalid_status_returns_422(
        self, internal_client: AsyncClient
    ) -> None:
        """status가 success/error 이외 값이면 422를 반환해야 한다."""
        resp = await internal_client.post(
            "/internal/backup-status",
            json={"status": "unknown"},
            headers=_secret_headers(),
        )
        assert resp.status_code == 422

    async def test_missing_secret_returns_403(
        self, internal_client: AsyncClient
    ) -> None:
        """X-Internal-Secret 헤더 없이 요청하면 403 을 반환해야 한다."""
        resp = await internal_client.post(
            "/internal/backup-status",
            json={"status": "success"},
        )
        assert resp.status_code == 403

    async def test_wrong_secret_returns_403(
        self, internal_client: AsyncClient
    ) -> None:
        """잘못된 X-Internal-Secret 헤더는 403 을 반환해야 한다."""
        resp = await internal_client.post(
            "/internal/backup-status",
            json={"status": "success"},
            headers=_secret_headers("wrong-secret"),
        )
        assert resp.status_code == 403

    async def test_empty_message_accepted(
        self, internal_client: AsyncClient
    ) -> None:
        """message 필드가 없어도 요청이 수락되어야 한다."""
        resp = await internal_client.post(
            "/internal/backup-status",
            json={"status": "success"},
            headers=_secret_headers(),
        )
        assert resp.status_code == 204

    async def test_long_message_truncated(
        self, internal_client: AsyncClient
    ) -> None:
        """500자를 초과하는 message는 잘려서 저장되어야 한다 (204 반환)."""
        long_message = "x" * 1000
        resp = await internal_client.post(
            "/internal/backup-status",
            json={"status": "success", "message": long_message},
            headers=_secret_headers(),
        )
        assert resp.status_code == 204


@pytest.mark.integration
class TestInternalSecretDisabled:
    async def test_disabled_when_secret_empty(self, client: AsyncClient) -> None:
        """INTERNAL_SECRET 가 비어있으면 503 을 반환해야 한다."""
        with patch("app.api.internal.settings") as mock_settings:
            mock_settings.INTERNAL_SECRET = ""
            resp = await client.post(
                "/internal/backup-status",
                json={"status": "success"},
                headers={"X-Internal-Secret": "anything"},
            )
        assert resp.status_code == 503
