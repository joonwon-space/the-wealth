"""Tests for api/stocks.py — stock search and detail endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _add_kis_account(client: AsyncClient, token: str) -> None:
    await client.post(
        "/users/kis-accounts",
        json={
            "label": "Test",
            "account_no": "12345678",
            "acnt_prdt_cd": "01",
            "app_key": "dummy_key",
            "app_secret": "dummy_secret",
        },
        headers=_auth(token),
    )


def _make_kis_detail_resp(output: dict) -> MagicMock:
    """Build a mock httpx.Response with KIS stock detail output."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"output": output}
    return mock_resp


def _sample_kis_output() -> dict:
    return {
        "stck_prpr": "75000",
        "stck_oprc": "73000",
        "stck_hgpr": "76000",
        "stck_lwpr": "72000",
        "stck_sdpr": "74000",
        "acml_vol": "5000000",
        "prdy_ctrt": "1.35",
        "hts_avls": "4500000",
        "per": "12.5",
        "pbr": "1.2",
        "eps": "6000",
        "bps": "62500",
        "w52_hgpr": "88000",
        "w52_lwpr": "55000",
    }


# ---------------------------------------------------------------------------
# Tests — search endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStockSearchEndpoint:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/stocks/search", params={"q": "삼성"})
        assert resp.status_code == 401

    async def test_missing_query_returns_422(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ss1@test.com")
        resp = await client.get("/stocks/search", headers=_auth(token))
        assert resp.status_code == 422

    async def test_search_returns_items(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ss2@test.com")

        mock_results = [
            {"ticker": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"ticker": "005935", "name": "삼성전자우", "market": "KOSPI"},
        ]
        with patch(
            "app.api.stocks._search",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            resp = await client.get(
                "/stocks/search", params={"q": "삼성"}, headers=_auth(token)
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["ticker"] == "005930"

    async def test_search_empty_results(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "ss3@test.com")

        with patch(
            "app.api.stocks._search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                "/stocks/search", params={"q": "XYZXYZ"}, headers=_auth(token)
            )

        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_search_service_error_returns_empty_items(
        self, client: AsyncClient
    ) -> None:
        """Service exception is swallowed; returns empty items with message."""
        token = await _register_and_login(client, "ss4@test.com")

        with patch(
            "app.api.stocks._search",
            new_callable=AsyncMock,
            side_effect=RuntimeError("search failed"),
        ):
            resp = await client.get(
                "/stocks/search", params={"q": "삼성"}, headers=_auth(token)
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert "message" in data


# ---------------------------------------------------------------------------
# Tests — detail endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStockDetailEndpoint:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/stocks/005930/detail")
        assert resp.status_code == 401

    async def test_no_kis_account_returns_error_field(
        self, client: AsyncClient
    ) -> None:
        """No KIS account → 200 with error field (not 4xx)."""
        token = await _register_and_login(client, "sd1@test.com")
        resp = await client.get("/stocks/005930/detail", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "005930"
        assert "error" in data

    async def test_detail_with_kis_account_returns_price_data(
        self, client: AsyncClient
    ) -> None:
        """With a KIS account, stock detail data is returned."""
        token = await _register_and_login(client, "sd2@test.com")
        await _add_kis_account(client, token)

        output = _sample_kis_output()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_make_kis_detail_resp(output))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.api.stocks.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.stocks.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get("/stocks/005930/detail", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["current_price"] == 75000.0
        assert data["open"] == 73000.0
        assert data["high"] == 76000.0
        assert data["low"] == 72000.0
        assert data["per"] == 12.5
        assert data["pbr"] == 1.2
        assert data["w52_high"] == 88000.0
        assert data["w52_low"] == 55000.0

    async def test_detail_kis_api_failure_returns_error_field(
        self, client: AsyncClient
    ) -> None:
        """KIS API error → 200 with error field (graceful degradation)."""
        token = await _register_and_login(client, "sd3@test.com")
        await _add_kis_account(client, token)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=RuntimeError("KIS down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.api.stocks.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.stocks.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get("/stocks/005930/detail", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    async def test_detail_includes_my_holding_when_present(
        self, client: AsyncClient
    ) -> None:
        """If user holds the stock, my_holding field is populated."""
        token = await _register_and_login(client, "sd4@test.com")
        await _add_kis_account(client, token)

        # Create portfolio and holding
        port = await client.post(
            "/portfolios", json={"name": "P"}, headers=_auth(token)
        )
        pid = port.json()["id"]
        await client.post(
            f"/portfolios/{pid}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
            headers=_auth(token),
        )

        output = _sample_kis_output()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_make_kis_detail_resp(output))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.api.stocks.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.stocks.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get("/stocks/005930/detail", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["my_holding"] is not None
        assert data["my_holding"]["quantity"] == 10.0
        assert data["my_holding"]["avg_price"] == 70000.0

    async def test_detail_my_holding_none_when_not_held(
        self, client: AsyncClient
    ) -> None:
        """If user does not hold the stock, my_holding is None."""
        token = await _register_and_login(client, "sd5@test.com")
        await _add_kis_account(client, token)

        output = _sample_kis_output()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_make_kis_detail_resp(output))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.api.stocks.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.stocks.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get("/stocks/TSLA/detail", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["my_holding"] is None

    async def test_detail_zero_values_are_none(self, client: AsyncClient) -> None:
        """Output fields with value '0' are returned as None."""
        token = await _register_and_login(client, "sd6@test.com")
        await _add_kis_account(client, token)

        # per=0, pbr=0 should return None
        output = {**_sample_kis_output(), "per": "0", "pbr": "0"}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=_make_kis_detail_resp(output))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.api.stocks.get_kis_access_token", new_callable=AsyncMock, return_value="tok"),
            patch("app.api.stocks.httpx.AsyncClient", return_value=mock_client),
        ):
            resp = await client.get("/stocks/005930/detail", headers=_auth(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["per"] is None
        assert data["pbr"] is None
