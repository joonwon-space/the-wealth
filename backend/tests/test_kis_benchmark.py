"""kis_benchmark.py 단위 테스트 — KIS API mocking."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kis_benchmark import (
    IndexSnapshotData,
    _fetch_domestic_index,
    _fetch_overseas_index,
    collect_snapshots,
)


# ─── _fetch_domestic_index ────────────────────────────────────────────────────


@pytest.mark.unit
class TestFetchDomesticIndex:
    @patch("app.services.kis_benchmark.get_kis_access_token", new_callable=AsyncMock)
    async def test_success(self, mock_token: AsyncMock) -> None:
        """정상 응답에서 IndexSnapshotData를 반환해야 한다."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "rt_cd": "0",
            "output": {
                "bstp_nmix_prpr": "2580.50",
                "bstp_nmix_prdy_ctrt": "1.23",
            },
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_ctx):
            result = await _fetch_domestic_index("key", "secret", "KOSPI200", "FHKUP03500100")

        assert result is not None
        assert result.index_code == "KOSPI200"
        assert result.close_price == Decimal("2580.50")
        assert result.change_pct == Decimal("1.23")

    @patch("app.services.kis_benchmark.get_kis_access_token", new_callable=AsyncMock)
    async def test_api_error_returns_none(self, mock_token: AsyncMock) -> None:
        """KIS API rt_cd != 0 이면 None을 반환해야 한다."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "rt_cd": "1",
            "msg1": "ERROR",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_ctx):
            result = await _fetch_domestic_index("key", "secret", "KOSPI200", "FHKUP03500100")

        assert result is None

    @patch("app.services.kis_benchmark.get_kis_access_token", new_callable=AsyncMock)
    async def test_network_exception_returns_none(self, mock_token: AsyncMock) -> None:
        """네트워크 오류 시 None을 반환해야 한다."""
        mock_token.return_value = "test-token"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_ctx):
            result = await _fetch_domestic_index("key", "secret", "KOSPI200", "FHKUP03500100")

        assert result is None

    @patch("app.services.kis_benchmark.get_kis_access_token", new_callable=AsyncMock)
    async def test_empty_price_returns_none(self, mock_token: AsyncMock) -> None:
        """가격 데이터가 없으면 None을 반환해야 한다."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "rt_cd": "0",
            "output": {},
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_ctx):
            result = await _fetch_domestic_index("key", "secret", "KOSPI200", "FHKUP03500100")

        assert result is None


# ─── _fetch_overseas_index ────────────────────────────────────────────────────


@pytest.mark.unit
class TestFetchOverseasIndex:
    @patch("app.services.kis_benchmark.get_kis_access_token", new_callable=AsyncMock)
    async def test_success(self, mock_token: AsyncMock) -> None:
        """S&P500 정상 응답에서 IndexSnapshotData를 반환해야 한다."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "rt_cd": "0",
            "output": {
                "last": "5,123.45",
                "rate": "-0.52",
            },
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_ctx):
            result = await _fetch_overseas_index("key", "secret", "SP500", "FHKST03030100")

        assert result is not None
        assert result.index_code == "SP500"
        assert result.close_price == Decimal("5123.45")
        assert result.change_pct == Decimal("-0.52")

    @patch("app.services.kis_benchmark.get_kis_access_token", new_callable=AsyncMock)
    async def test_api_error_returns_none(self, mock_token: AsyncMock) -> None:
        """KIS API 오류 시 None을 반환해야 한다."""
        mock_token.return_value = "test-token"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"rt_cd": "1", "msg1": "OVRS ERROR"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_ctx):
            result = await _fetch_overseas_index("key", "secret", "SP500", "FHKST03030100")

        assert result is None


# ─── collect_snapshots ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCollectSnapshots:
    @patch("app.services.kis_benchmark._upsert_snapshot", new_callable=AsyncMock)
    @patch("app.services.kis_benchmark._fetch_overseas_index", new_callable=AsyncMock)
    @patch("app.services.kis_benchmark._fetch_domestic_index", new_callable=AsyncMock)
    async def test_both_succeed(
        self,
        mock_domestic: AsyncMock,
        mock_overseas: AsyncMock,
        mock_upsert: AsyncMock,
    ) -> None:
        """두 지수 모두 성공 시 {'KOSPI200': True, 'SP500': True} 반환."""
        from datetime import datetime, timezone

        mock_domestic.return_value = IndexSnapshotData(
            index_code="KOSPI200",
            timestamp=datetime.now(timezone.utc),
            close_price=Decimal("2580.50"),
            change_pct=Decimal("1.23"),
        )
        mock_overseas.return_value = IndexSnapshotData(
            index_code="SP500",
            timestamp=datetime.now(timezone.utc),
            close_price=Decimal("5123.45"),
            change_pct=Decimal("-0.52"),
        )
        mock_upsert.return_value = None

        result = await collect_snapshots("key", "secret")

        assert result == {"KOSPI200": True, "SP500": True}
        assert mock_upsert.call_count == 2

    @patch("app.services.kis_benchmark._upsert_snapshot", new_callable=AsyncMock)
    @patch("app.services.kis_benchmark._fetch_overseas_index", new_callable=AsyncMock)
    @patch("app.services.kis_benchmark._fetch_domestic_index", new_callable=AsyncMock)
    async def test_one_fails_other_succeeds(
        self,
        mock_domestic: AsyncMock,
        mock_overseas: AsyncMock,
        mock_upsert: AsyncMock,
    ) -> None:
        """한 지수 실패 시 해당 지수만 False, 나머지는 True."""
        from datetime import datetime, timezone

        mock_domestic.return_value = None  # KOSPI200 실패
        mock_overseas.return_value = IndexSnapshotData(
            index_code="SP500",
            timestamp=datetime.now(timezone.utc),
            close_price=Decimal("5123.45"),
            change_pct=None,
        )
        mock_upsert.return_value = None

        result = await collect_snapshots("key", "secret")

        assert result["KOSPI200"] is False
        assert result["SP500"] is True
        assert mock_upsert.call_count == 1

    @patch("app.services.kis_benchmark._upsert_snapshot", new_callable=AsyncMock)
    @patch("app.services.kis_benchmark._fetch_overseas_index", new_callable=AsyncMock)
    @patch("app.services.kis_benchmark._fetch_domestic_index", new_callable=AsyncMock)
    async def test_upsert_failure_marks_false(
        self,
        mock_domestic: AsyncMock,
        mock_overseas: AsyncMock,
        mock_upsert: AsyncMock,
    ) -> None:
        """upsert 실패 시 해당 지수 False로 처리."""
        from datetime import datetime, timezone

        snap = IndexSnapshotData(
            index_code="KOSPI200",
            timestamp=datetime.now(timezone.utc),
            close_price=Decimal("2580.50"),
            change_pct=None,
        )
        mock_domestic.return_value = snap
        mock_overseas.return_value = None
        mock_upsert.side_effect = Exception("DB error")

        result = await collect_snapshots("key", "secret")

        assert result["KOSPI200"] is False
        assert result["SP500"] is False
