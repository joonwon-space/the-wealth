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


@pytest.fixture(autouse=True)
def _reset_kis_availability():
    """매 테스트마다 KIS 가용성 글로벌 상태를 True로 초기화한다.

    `_kis_availability`는 모듈 레벨 싱글톤이라 한 테스트가 False로 만들면
    이후 테스트가 cache-only 모드로 빠져 결과가 달라진다. autouse로 매번
    초기 상태로 되돌려 테스트 간 누수를 막는다.
    """
    from app.services.kis_health import set_kis_availability

    set_kis_availability(True, "")
    yield
    set_kis_availability(True, "")


@pytest.fixture(autouse=True)
def _disable_login_bg_sync(monkeypatch):
    """`/auth/login` 응답 후 실행되는 _bg_sync_user 백그라운드 태스크를 비활성화한다.

    프로덕션에서는 login 응답 반환 즉시 KIS 잔고 동기화를 백그라운드로 돌리지만,
    테스트 환경에서는:
    1. 진짜 KIS URL 로 connect 시도 → kis_call_slot rate token / concurrency 잡고
       fixture teardown 까지 살아있음
    2. teardown 후 event loop close → "Event loop is closed" / "attached to a
       different loop" flaky failure

    test 함수 자체에서 sync 가 필요하면 명시적으로 호출하면 된다.
    """
    async def _noop(user_id: int) -> None:  # noqa: ARG001
        return

    monkeypatch.setattr("app.api.auth._bg_sync_user", _noop)


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
async def test_session_factory():
    """Yield an async_sessionmaker bound to the test DB.

    Unlike the ``db`` fixture this does NOT clean table data — it is meant
    for tests that have already set up data via the ``client`` fixture and
    need a raw session to call service functions directly.
    """
    engine = _make_engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()
    await asyncio.sleep(0)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide HTTP client with clean data for each test."""
    from app.core.limiter import limiter
    from app.db.session import get_db
    from app.main import app

    from app.core.redis_cache import reset_fallback_cache

    await _clean_all_data()
    await _flush_redis_cache()
    reset_fallback_cache()  # reset pool so it binds to the current event loop

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
