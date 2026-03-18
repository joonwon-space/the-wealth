"""워치리스트 API 통합 테스트 (CRUD, 중복 409, IDOR 방지, 빈 ticker 검증)."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "watch@example.com"
) -> str:
    """Helper: register user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestWatchlistCRUD:
    async def test_list_watchlist_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_list_empty@example.com")
        resp = await client.get("/watchlist", headers=_auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_add_to_watchlist(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_add@example.com")
        resp = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["name"] == "삼성전자"
        assert data["market"] == "KRX"
        assert "id" in data

    async def test_add_and_list_watchlist(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_addlist@example.com")
        await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token),
        )
        await client.post(
            "/watchlist",
            json={"ticker": "000660", "name": "SK하이닉스", "market": "KRX"},
            headers=_auth_headers(token),
        )
        resp = await client.get("/watchlist", headers=_auth_headers(token))
        assert resp.status_code == 200
        tickers = {item["ticker"] for item in resp.json()}
        assert {"005930", "000660"} == tickers

    async def test_delete_from_watchlist(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_delete@example.com")
        add_resp = await client.post(
            "/watchlist",
            json={"ticker": "035420", "name": "NAVER", "market": "KRX"},
            headers=_auth_headers(token),
        )
        item_id = add_resp.json()["id"]
        del_resp = await client.delete(
            f"/watchlist/{item_id}", headers=_auth_headers(token)
        )
        assert del_resp.status_code == 204

        # Verify it's gone
        list_resp = await client.get("/watchlist", headers=_auth_headers(token))
        assert all(item["id"] != item_id for item in list_resp.json())

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_del404@example.com")
        resp = await client.delete("/watchlist/99999", headers=_auth_headers(token))
        assert resp.status_code == 404

    async def test_unauthenticated_list_denied(self, client: AsyncClient) -> None:
        resp = await client.get("/watchlist")
        assert resp.status_code in (401, 403)

    async def test_unauthenticated_add_denied(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.integration
class TestWatchlistDuplicate:
    async def test_duplicate_ticker_returns_409(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_dup@example.com")
        await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token),
        )
        resp = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 409

    async def test_same_ticker_different_users_allowed(self, client: AsyncClient) -> None:
        """Same ticker can be added by different users without conflict."""
        token_a = await _register_and_get_token(client, "wl_dup_a@example.com")
        token_b = await _register_and_get_token(client, "wl_dup_b@example.com")

        resp_a = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token_a),
        )
        resp_b = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token_b),
        )
        assert resp_a.status_code == 201
        assert resp_b.status_code == 201


@pytest.mark.integration
class TestWatchlistIDOR:
    async def test_cannot_delete_other_users_item(self, client: AsyncClient) -> None:
        """User B cannot delete User A's watchlist item."""
        token_a = await _register_and_get_token(client, "wl_idor_a@example.com")
        token_b = await _register_and_get_token(client, "wl_idor_b@example.com")

        add_resp = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token_a),
        )
        item_id = add_resp.json()["id"]

        # User B tries to delete User A's item
        del_resp = await client.delete(
            f"/watchlist/{item_id}", headers=_auth_headers(token_b)
        )
        assert del_resp.status_code == 404

        # Verify item still exists for User A
        list_resp = await client.get("/watchlist", headers=_auth_headers(token_a))
        assert any(item["id"] == item_id for item in list_resp.json())

    async def test_list_only_returns_own_items(self, client: AsyncClient) -> None:
        """GET /watchlist returns only items belonging to the authenticated user."""
        token_a = await _register_and_get_token(client, "wl_scope_a@example.com")
        token_b = await _register_and_get_token(client, "wl_scope_b@example.com")

        await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "KRX"},
            headers=_auth_headers(token_a),
        )
        await client.post(
            "/watchlist",
            json={"ticker": "000660", "name": "SK하이닉스", "market": "KRX"},
            headers=_auth_headers(token_b),
        )

        resp_a = await client.get("/watchlist", headers=_auth_headers(token_a))
        resp_b = await client.get("/watchlist", headers=_auth_headers(token_b))

        tickers_a = {item["ticker"] for item in resp_a.json()}
        tickers_b = {item["ticker"] for item in resp_b.json()}

        assert tickers_a == {"005930"}
        assert tickers_b == {"000660"}


@pytest.mark.integration
class TestWatchlistValidation:
    async def test_empty_ticker_rejected(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_empty_ticker@example.com")
        resp = await client.post(
            "/watchlist",
            json={"ticker": "", "name": "빈 티커", "market": "KRX"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_whitespace_only_ticker_rejected(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_ws_ticker@example.com")
        resp = await client.post(
            "/watchlist",
            json={"ticker": "   ", "name": "공백 티커", "market": "KRX"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_invalid_market_rejected(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wl_bad_market@example.com")
        resp = await client.post(
            "/watchlist",
            json={"ticker": "005930", "name": "삼성전자", "market": "INVALID"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_ticker_uppercased_automatically(self, client: AsyncClient) -> None:
        """Lowercase ticker should be stored as uppercase."""
        token = await _register_and_get_token(client, "wl_upper@example.com")
        resp = await client.post(
            "/watchlist",
            json={"ticker": "aapl", "name": "Apple", "market": "NYSE"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        assert resp.json()["ticker"] == "AAPL"

    async def test_valid_markets_accepted(self, client: AsyncClient) -> None:
        """All valid market values (KRX, NYSE, NASDAQ, AMEX) should be accepted."""
        token = await _register_and_get_token(client, "wl_markets@example.com")
        valid_cases = [
            ("005930", "삼성전자", "KRX"),
            ("AAPL", "Apple", "NYSE"),
            ("MSFT", "Microsoft", "NASDAQ"),
            ("GME", "GameStop", "AMEX"),
        ]
        for ticker, name, market in valid_cases:
            resp = await client.post(
                "/watchlist",
                json={"ticker": ticker, "name": name, "market": market},
                headers=_auth_headers(token),
            )
            assert resp.status_code == 201, f"Expected 201 for market={market}, got {resp.status_code}"
