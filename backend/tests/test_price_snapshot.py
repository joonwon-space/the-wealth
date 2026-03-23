"""Unit tests for price snapshot service: save_snapshots, save_ohlcv_snapshots,
get_prev_close, and fetch_domestic_price_detail."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.price_snapshot import (
    OhlcvData,
    fetch_domestic_price_detail,
    get_prev_close,
    save_ohlcv_snapshots,
    save_snapshots,
)


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


@pytest.mark.integration
class TestSaveOhlcvSnapshots:
    """Integration tests for save_ohlcv_snapshots."""

    async def test_saves_single_ohlcv(self, db: AsyncSession) -> None:
        ohlcv_map = {
            "005930": OhlcvData(
                open=Decimal("74000"),
                high=Decimal("76000"),
                low=Decimal("73500"),
                close=Decimal("75000"),
                volume=12345678,
            )
        }
        count = await save_ohlcv_snapshots(db, ohlcv_map, snapshot_date=date(2024, 1, 15))
        assert count == 1

    async def test_saves_multiple_ohlcv(self, db: AsyncSession) -> None:
        ohlcv_map = {
            "005930": OhlcvData(
                open=Decimal("74000"),
                high=Decimal("76000"),
                low=Decimal("73500"),
                close=Decimal("75000"),
                volume=1000,
            ),
            "000660": OhlcvData(
                open=Decimal("119000"),
                high=Decimal("122000"),
                low=Decimal("118000"),
                close=Decimal("120000"),
                volume=2000,
            ),
        }
        count = await save_ohlcv_snapshots(db, ohlcv_map, snapshot_date=date(2024, 1, 15))
        assert count == 2

    async def test_empty_map_returns_zero(self, db: AsyncSession) -> None:
        count = await save_ohlcv_snapshots(db, {}, snapshot_date=date(2024, 1, 15))
        assert count == 0

    async def test_upserts_on_conflict(self, db: AsyncSession) -> None:
        d = date(2024, 1, 15)
        ohlcv_map = {
            "005930": OhlcvData(
                open=Decimal("74000"),
                high=Decimal("76000"),
                low=Decimal("73000"),
                close=Decimal("75000"),
                volume=1000,
            )
        }
        await save_ohlcv_snapshots(db, ohlcv_map, snapshot_date=d)
        # Second upsert with different close
        ohlcv_map2 = {
            "005930": OhlcvData(
                open=Decimal("75000"),
                high=Decimal("77000"),
                low=Decimal("74000"),
                close=Decimal("76500"),
                volume=2000,
            )
        }
        count = await save_ohlcv_snapshots(db, ohlcv_map2, snapshot_date=d)
        assert count == 1
        # Verify updated close price
        result = await get_prev_close(db, ["005930"], ref_date=date(2024, 1, 16))
        assert result["005930"] == Decimal("76500")

    async def test_uses_today_when_date_not_given(self, db: AsyncSession) -> None:
        from datetime import datetime, timedelta, timezone

        today = datetime.now(timezone.utc).date()
        ohlcv_map = {
            "005930": OhlcvData(
                open=None,
                high=None,
                low=None,
                close=Decimal("75000"),
                volume=None,
            )
        }
        count = await save_ohlcv_snapshots(db, ohlcv_map)
        assert count == 1
        result = await get_prev_close(
            db, ["005930"], ref_date=today + timedelta(days=1)
        )
        assert "005930" in result

    async def test_ohlcv_with_none_fields(self, db: AsyncSession) -> None:
        """OHLCV with None open/high/low/volume (only close required)."""
        ohlcv_map = {
            "005930": OhlcvData(
                open=None,
                high=None,
                low=None,
                close=Decimal("75000"),
                volume=None,
            )
        }
        count = await save_ohlcv_snapshots(db, ohlcv_map, snapshot_date=date(2024, 1, 15))
        assert count == 1


@pytest.mark.unit
class TestFetchDomesticPriceDetail:
    """Unit tests for fetch_domestic_price_detail with httpx mocking."""

    def _make_http_client(self, response_body: dict, status_code: int = 200) -> MagicMock:
        """Build a mock httpx.AsyncClient that returns given body."""
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = response_body
        mock_resp.raise_for_status = MagicMock()
        if status_code >= 400:
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"HTTP {status_code}", request=MagicMock(), response=mock_resp
            )

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=mock_resp)
        return client

    @pytest.mark.asyncio
    async def test_returns_price_detail_on_success(self) -> None:
        body = {
            "output": {
                "stck_prpr": "75000",
                "stck_sdpr": "73000",
                "prdy_ctrt": "2.74",
                "w52_hgpr": "85000",
                "w52_lwpr": "55000",
            }
        }
        client = self._make_http_client(body)

        with patch(
            "app.services.price_snapshot.get_kis_access_token",
            new_callable=AsyncMock,
            return_value="mock_token",
        ):
            result = await fetch_domestic_price_detail(
                "005930", "app_key", "app_secret", client
            )

        assert result is not None
        assert result.current == Decimal("75000")
        assert result.prev_close == Decimal("73000")
        assert result.day_change_rate == Decimal("2.74")
        assert result.w52_high == Decimal("85000")
        assert result.w52_low == Decimal("55000")

    @pytest.mark.asyncio
    async def test_returns_none_when_price_is_zero(self) -> None:
        body = {
            "output": {
                "stck_prpr": "0",
                "stck_sdpr": "73000",
                "prdy_ctrt": "0",
            }
        }
        client = self._make_http_client(body)

        with patch(
            "app.services.price_snapshot.get_kis_access_token",
            new_callable=AsyncMock,
            return_value="mock_token",
        ):
            result = await fetch_domestic_price_detail(
                "005930", "app_key", "app_secret", client
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_price_is_empty_string(self) -> None:
        body = {
            "output": {
                "stck_prpr": "",
                "stck_sdpr": "73000",
                "prdy_ctrt": "0",
            }
        }
        client = self._make_http_client(body)

        with patch(
            "app.services.price_snapshot.get_kis_access_token",
            new_callable=AsyncMock,
            return_value="mock_token",
        ):
            result = await fetch_domestic_price_detail(
                "005930", "app_key", "app_secret", client
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self) -> None:
        client = self._make_http_client({}, status_code=401)

        with patch(
            "app.services.price_snapshot.get_kis_access_token",
            new_callable=AsyncMock,
            return_value="mock_token",
        ):
            result = await fetch_domestic_price_detail(
                "005930", "app_key", "app_secret", client
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_timeout(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch(
            "app.services.price_snapshot.get_kis_access_token",
            new_callable=AsyncMock,
            return_value="mock_token",
        ):
            result = await fetch_domestic_price_detail(
                "005930", "app_key", "app_secret", client
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_missing_w52_fields(self) -> None:
        """w52_high and w52_low are optional — missing fields return None."""
        body = {
            "output": {
                "stck_prpr": "75000",
                "stck_sdpr": "73000",
                "prdy_ctrt": "2.74",
                # w52_hgpr and w52_lwpr absent
            }
        }
        client = self._make_http_client(body)

        with patch(
            "app.services.price_snapshot.get_kis_access_token",
            new_callable=AsyncMock,
            return_value="mock_token",
        ):
            result = await fetch_domestic_price_detail(
                "005930", "app_key", "app_secret", client
            )

        assert result is not None
        assert result.w52_high is None
        assert result.w52_low is None
