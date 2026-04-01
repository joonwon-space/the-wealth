"""Shared test fixtures for backend tests.

Architecture:
- Schema is created ONCE per session (via session-scoped autouse fixture).
- Data is cleaned between tests (DELETE rows, not DROP/CREATE tables).
- Each test gets its own NullPool engine to avoid cross-loop asyncpg conflicts.

This eliminates ENUM type conflicts and table-not-found errors while keeping
tests isolated from each other.
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)
TEST_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


async def _flush_redis_cache() -> None:
    """테스트 간 Redis analytics/price 캐시를 제거하여 캐시 오염을 방지한다."""
    try:
        r = aioredis.from_url(TEST_REDIS_URL)
        keys = await r.keys("analytics:*")
        if keys:
            await r.delete(*keys)
        await r.aclose()
    except Exception:
        pass  # Redis 미사용 환경에서는 무시


def _make_engine():
    """Create a NullPool async engine for the test database."""
    return create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Create the DB schema ONCE before all tests, drop it ONCE after all tests.

    Uses a sync approach to avoid event loop scope conflicts.
    """
    import asyncio
    from app.db.base import Base
    import app.models  # noqa: F401 — register all models with Base.metadata

    async def _setup() -> None:
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    async def _teardown() -> None:
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_setup())
    yield
    loop.run_until_complete(_teardown())
    loop.close()


async def _clean_all_data() -> None:
    """Delete all rows from all tables (keeps schema intact).

    Iterates tables in reverse FK order so child rows are deleted before parents.
    If a table is missing (e.g. dropped by a rogue duplicate test file), the schema
    is recreated before cleaning so subsequent tests start with a fresh slate.
    """
    from app.db.base import Base
    import app.models  # noqa: F401

    engine = _make_engine()
    try:
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
    except Exception:
        # Schema was dropped externally (e.g. by duplicate test file) — recreate it.
        await engine.dispose()
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a DB session with clean data for each test."""
    await _clean_all_data()

    engine = _make_engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
    await asyncio.sleep(0)  # asyncpg cancel 코루틴이 처리될 기회를 줌


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide HTTP client with clean data for each test."""
    from app.core.limiter import limiter
    from app.db.session import get_db
    from app.main import app

    await _clean_all_data()
    await _flush_redis_cache()

    # Reset in-memory rate limit counters before each test
    try:
        limiter._storage.reset()  # type: ignore[attr-defined]
    except Exception:
        pass  # Storage may not support reset; best-effort

    engine = _make_engine()
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
    await asyncio.sleep(0)  # asyncpg cancel 코루틴이 처리될 기회를 줌
