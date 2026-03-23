"""Shared test fixtures for backend tests.

Each test gets a fresh DB setup to avoid event loop issues on Python 3.9.
"""

import os
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client with a fresh test DB and reset rate limits."""
    from app.core.limiter import limiter
    from app.db.base import Base
    from app.db.session import get_db
    from app.main import app

    # Reset in-memory rate limit counters before each test
    # This prevents rate limits from one test bleeding into another
    try:
        limiter._storage.reset()  # type: ignore[attr-defined]
    except Exception:
        pass  # Storage may not support reset; best-effort

    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
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
