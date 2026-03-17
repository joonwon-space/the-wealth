"""Unit tests for price snapshot service: save_snapshots, get_prev_close."""

from datetime import date
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.price_snapshot import get_prev_close, save_snapshots

import os

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://joonwon@localhost:5432/the_wealth_test",
)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    from app.db.base import Base

    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.integration
class TestSaveSnapshots:
    async def test_save_single_ticker(self, db: AsyncSession) -> None:
        prices = {"005930": Decimal("75000")}
        count = await save_snapshots(db, prices, snapshot_date=date(2024, 1, 15))
        assert count == 1

    async def test_save_multiple_tickers(self, db: AsyncSession) -> None:
        prices = {
            "005930": Decimal("75000"),
            "000660": Decimal("120000"),
            "035420": Decimal("200000"),
        }
        count = await save_snapshots(db, prices, snapshot_date=date(2024, 1, 15))
        assert count == 3

    async def test_empty_dict_returns_zero(self, db: AsyncSession) -> None:
        count = await save_snapshots(db, {}, snapshot_date=date(2024, 1, 15))
        assert count == 0

    async def test_upsert_updates_existing(self, db: AsyncSession) -> None:
        d = date(2024, 1, 15)
        await save_snapshots(db, {"005930": Decimal("75000")}, snapshot_date=d)
        # Save again with different price — should update, not duplicate
        count = await save_snapshots(db, {"005930": Decimal("76500")}, snapshot_date=d)
        assert count == 1
        # Verify the updated price is reflected by querying prev_close from next day
        result = await get_prev_close(db, ["005930"], ref_date=date(2024, 1, 16))
        assert result["005930"] == Decimal("76500")

    async def test_save_uses_today_when_date_not_given(self, db: AsyncSession) -> None:
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date()
        prices = {"005930": Decimal("75000")}
        count = await save_snapshots(db, prices)
        assert count == 1
        # Can be retrieved as prev_close for tomorrow
        from datetime import timedelta

        result = await get_prev_close(
            db, ["005930"], ref_date=today + timedelta(days=1)
        )
        assert "005930" in result


@pytest.mark.integration
class TestGetPrevClose:
    async def test_returns_empty_for_no_snapshots(self, db: AsyncSession) -> None:
        result = await get_prev_close(db, ["005930"], ref_date=date(2024, 1, 15))
        assert result == {}

    async def test_returns_empty_for_empty_tickers(self, db: AsyncSession) -> None:
        result = await get_prev_close(db, [], ref_date=date(2024, 1, 15))
        assert result == {}

    async def test_returns_most_recent_before_ref_date(self, db: AsyncSession) -> None:
        await save_snapshots(db, {"005930": Decimal("70000")}, snapshot_date=date(2024, 1, 10))
        await save_snapshots(db, {"005930": Decimal("72000")}, snapshot_date=date(2024, 1, 12))
        await save_snapshots(db, {"005930": Decimal("75000")}, snapshot_date=date(2024, 1, 14))

        # ref_date=2024-01-15 → should return 2024-01-14 close
        result = await get_prev_close(db, ["005930"], ref_date=date(2024, 1, 15))
        assert result["005930"] == Decimal("75000")

    async def test_excludes_same_day_snapshot(self, db: AsyncSession) -> None:
        await save_snapshots(db, {"005930": Decimal("75000")}, snapshot_date=date(2024, 1, 15))

        # ref_date=2024-01-15 should NOT return same-day snapshot
        result = await get_prev_close(db, ["005930"], ref_date=date(2024, 1, 15))
        assert result == {}

    async def test_returns_only_requested_tickers(self, db: AsyncSession) -> None:
        await save_snapshots(
            db,
            {"005930": Decimal("75000"), "000660": Decimal("120000")},
            snapshot_date=date(2024, 1, 14),
        )

        result = await get_prev_close(db, ["005930"], ref_date=date(2024, 1, 15))
        assert "005930" in result
        assert "000660" not in result

    async def test_handles_multiple_tickers(self, db: AsyncSession) -> None:
        await save_snapshots(
            db,
            {"005930": Decimal("75000"), "000660": Decimal("120000")},
            snapshot_date=date(2024, 1, 14),
        )

        result = await get_prev_close(
            db, ["005930", "000660"], ref_date=date(2024, 1, 15)
        )
        assert result["005930"] == Decimal("75000")
        assert result["000660"] == Decimal("120000")

    async def test_ticker_not_in_snapshots_absent_from_result(
        self, db: AsyncSession
    ) -> None:
        await save_snapshots(
            db, {"005930": Decimal("75000")}, snapshot_date=date(2024, 1, 14)
        )

        result = await get_prev_close(
            db, ["005930", "999999"], ref_date=date(2024, 1, 15)
        )
        assert "005930" in result
        assert "999999" not in result
