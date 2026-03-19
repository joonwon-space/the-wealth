"""Unit tests for app/services/kis_account.py.

Tests fetch_account_holdings and fetch_overseas_account_holdings with
httpx response mocking. Target: 85%+ coverage.
"""

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.kis_account import (
    KisHolding,
    fetch_account_holdings,
    fetch_overseas_account_holdings,
)


def _make_resp(status_code: int, json_body: dict[str, Any]) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_body)
    if status_code >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                f"HTTP {status_code}",
                request=MagicMock(),
                response=resp,
            )
        )
    else:
        resp.raise_for_status = MagicMock(return_value=None)
    return resp


# ---------------------------------------------------------------------------
# KisHolding dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKisHoldingDataclass:
    def test_creation_with_required_fields(self) -> None:
        h = KisHolding(
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
        )
        assert h.ticker == "005930"
        assert h.name == "삼성전자"
        assert h.market is None

    def test_creation_with_market(self) -> None:
        h = KisHolding(
            ticker="AAPL",
            name="Apple Inc",
            quantity=Decimal("5"),
            avg_price=Decimal("185.50"),
            market="NAS",
        )
        assert h.market == "NAS"

    def test_immutable_frozen(self) -> None:
        h = KisHolding(
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
        )
        with pytest.raises((AttributeError, TypeError)):
            h.ticker = "000000"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# fetch_account_holdings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchAccountHoldings:
    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_success_returns_holdings(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(
            200,
            {
                "rt_cd": "0",
                "output1": [
                    {
                        "pdno": "005930",
                        "prdt_name": "삼성전자",
                        "hldg_qty": "10",
                        "pchs_avg_pric": "70000",
                    }
                ],
            },
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_account_holdings("key", "secret", "12345678")
        assert len(result) == 1
        assert result[0].ticker == "005930"
        assert result[0].quantity == Decimal("10")
        assert result[0].avg_price == Decimal("70000")

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_zero_quantity_holdings_filtered(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        """Holdings with qty <= 0 must be excluded."""
        mock_token.return_value = "fake-token"
        response = _make_resp(
            200,
            {
                "rt_cd": "0",
                "output1": [
                    {"pdno": "005930", "prdt_name": "삼성전자", "hldg_qty": "0", "pchs_avg_pric": "70000"},
                    {"pdno": "000660", "prdt_name": "SK하이닉스", "hldg_qty": "5", "pchs_avg_pric": "120000"},
                ],
            },
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_account_holdings("key", "secret", "12345678")
        assert len(result) == 1
        assert result[0].ticker == "000660"

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_non_zero_rt_cd_returns_empty(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        """rt_cd != '0' means API-level error → empty list."""
        mock_token.return_value = "fake-token"
        response = _make_resp(200, {"rt_cd": "1", "msg1": "Invalid account"})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_account_holdings("key", "secret", "12345678")
        assert result == []

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_empty_output1_returns_empty_list(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(200, {"rt_cd": "0", "output1": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_account_holdings("key", "secret", "12345678")
        assert result == []

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_http_401_returns_empty(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(401, {})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_account_holdings("key", "secret", "12345678")
        assert result == []

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_timeout_returns_empty(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("t/o"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_account_holdings("key", "secret", "12345678")
        assert result == []

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_custom_product_code(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        """account_product_code parameter is passed through."""
        mock_token.return_value = "fake-token"
        response = _make_resp(200, {"rt_cd": "0", "output1": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        await fetch_account_holdings("key", "secret", "12345678", account_product_code="02")
        call_kwargs = mock_client.get.await_args[1]
        assert call_kwargs["params"]["ACNT_PRDT_CD"] == "02"

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_multiple_holdings(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(
            200,
            {
                "rt_cd": "0",
                "output1": [
                    {"pdno": "005930", "prdt_name": "삼성전자", "hldg_qty": "10", "pchs_avg_pric": "70000"},
                    {"pdno": "000660", "prdt_name": "SK하이닉스", "hldg_qty": "5", "pchs_avg_pric": "120000"},
                    {"pdno": "035420", "prdt_name": "NAVER", "hldg_qty": "2", "pchs_avg_pric": "180000"},
                ],
            },
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_account_holdings("key", "secret", "12345678")
        assert len(result) == 3
        tickers = [h.ticker for h in result]
        assert "005930" in tickers
        assert "000660" in tickers
        assert "035420" in tickers


# ---------------------------------------------------------------------------
# fetch_overseas_account_holdings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchOverseasAccountHoldings:
    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_success_returns_holdings(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(
            200,
            {
                "rt_cd": "0",
                "output1": [
                    {
                        "ovrs_pdno": "AAPL",
                        "ovrs_item_name": "Apple Inc",
                        "ovrs_cblc_qty": "5",
                        "pchs_avg_pric": "185.50",
                        "ovrs_excg_cd": "NAS",
                    }
                ],
            },
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        holdings, summary = await fetch_overseas_account_holdings("key", "secret", "12345678")
        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"
        assert holdings[0].quantity == Decimal("5")
        assert holdings[0].market == "NAS"
        assert isinstance(summary, dict)

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_zero_quantity_filtered(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(
            200,
            {
                "rt_cd": "0",
                "output1": [
                    {
                        "ovrs_pdno": "AAPL",
                        "ovrs_item_name": "Apple",
                        "ovrs_cblc_qty": "0",
                        "pchs_avg_pric": "185.0",
                        "ovrs_excg_cd": "NAS",
                    },
                    {
                        "ovrs_pdno": "MSFT",
                        "ovrs_item_name": "Microsoft",
                        "ovrs_cblc_qty": "3",
                        "pchs_avg_pric": "320.0",
                        "ovrs_excg_cd": "NAS",
                    },
                ],
            },
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        holdings, _ = await fetch_overseas_account_holdings("key", "secret", "12345678")
        assert len(holdings) == 1
        assert holdings[0].ticker == "MSFT"

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_non_zero_rt_cd_returns_empty(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(200, {"rt_cd": "E", "msg1": "Invalid"})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        holdings, summary = await fetch_overseas_account_holdings("key", "secret", "12345678")
        assert holdings == []
        assert summary == {}

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_http_429_returns_empty(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        response = _make_resp(429, {})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        holdings, summary = await fetch_overseas_account_holdings("key", "secret", "12345678")
        assert holdings == []
        assert summary == {}

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_timeout_returns_empty(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        mock_token.return_value = "fake-token"
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("t/o"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        holdings, summary = await fetch_overseas_account_holdings("key", "secret", "12345678")
        assert holdings == []
        assert summary == {}

    @patch("app.services.kis_account.get_kis_access_token", new_callable=AsyncMock)
    @patch("app.services.kis_account.httpx.AsyncClient")
    async def test_empty_ovrs_excg_cd_becomes_none(
        self, mock_client_cls: MagicMock, mock_token: AsyncMock
    ) -> None:
        """Empty ovrs_excg_cd → market=None via `or None`."""
        mock_token.return_value = "fake-token"
        response = _make_resp(
            200,
            {
                "rt_cd": "0",
                "output1": [
                    {
                        "ovrs_pdno": "TSLA",
                        "ovrs_item_name": "Tesla",
                        "ovrs_cblc_qty": "2",
                        "pchs_avg_pric": "250.0",
                        "ovrs_excg_cd": "",  # empty
                    }
                ],
            },
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        holdings, _ = await fetch_overseas_account_holdings("key", "secret", "12345678")
        assert len(holdings) == 1
        assert holdings[0].market is None
