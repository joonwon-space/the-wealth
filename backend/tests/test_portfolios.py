"""포트폴리오 CRUD API 통합 테스트."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "port@example.com"
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
class TestPortfolios:
    async def test_create_portfolio(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "create@example.com")
        resp = await client.post(
            "/portfolios",
            json={"name": "내 포트폴리오", "currency": "KRW"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "내 포트폴리오"
        assert data["currency"] == "KRW"
        assert "id" in data

    async def test_list_portfolios(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "list@example.com")
        await client.post(
            "/portfolios",
            json={"name": "포트폴리오 A"},
            headers=_auth_headers(token),
        )
        resp = await client.get("/portfolios", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    async def test_delete_portfolio(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "del@example.com")
        create_resp = await client.post(
            "/portfolios",
            json={"name": "삭제용"},
            headers=_auth_headers(token),
        )
        pid = create_resp.json()["id"]
        resp = await client.delete(f"/portfolios/{pid}", headers=_auth_headers(token))
        assert resp.status_code == 204

    async def test_delete_portfolio_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "del404@example.com")
        resp = await client.delete("/portfolios/99999", headers=_auth_headers(token))
        assert resp.status_code == 404

    async def test_unauthenticated_access(self, client: AsyncClient) -> None:
        resp = await client.get("/portfolios")
        assert resp.status_code in (401, 403)


@pytest.mark.integration
class TestHoldings:
    async def test_add_holding(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "hold@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "종목 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        resp = await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": 10,
                "avg_price": 70000,
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["name"] == "삼성전자"

    async def test_list_holdings(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "listh@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "목록 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": 5,
                "avg_price": 65000,
            },
            headers=_auth_headers(token),
        )
        resp = await client.get(
            f"/portfolios/{pid}/holdings", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_holding(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "upd@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "수정 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        hold = await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "035720",
                "name": "카카오",
                "quantity": 20,
                "avg_price": 50000,
            },
            headers=_auth_headers(token),
        )
        hid = hold.json()["id"]

        resp = await client.patch(
            f"/portfolios/holdings/{hid}",
            json={"quantity": 30},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert float(resp.json()["quantity"]) == 30

    async def test_delete_holding(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "delh@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "삭제 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        hold = await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "000660",
                "name": "SK하이닉스",
                "quantity": 15,
                "avg_price": 120000,
            },
            headers=_auth_headers(token),
        )
        hid = hold.json()["id"]

        resp = await client.delete(
            f"/portfolios/holdings/{hid}", headers=_auth_headers(token)
        )
        assert resp.status_code == 204


@pytest.mark.integration
class TestMultiplePortfoliosHoldings:
    """Verify holdings are correctly scoped to their portfolio and user."""

    async def test_holdings_isolated_between_portfolios(self, client: AsyncClient) -> None:
        """Holdings in portfolio A are not visible in portfolio B."""
        token = await _register_and_get_token(client, "multi1@example.com")
        port_a = (await client.post("/portfolios", json={"name": "A"}, headers=_auth_headers(token))).json()
        port_b = (await client.post("/portfolios", json={"name": "B"}, headers=_auth_headers(token))).json()

        await client.post(
            f"/portfolios/{port_a['id']}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
            headers=_auth_headers(token),
        )
        await client.post(
            f"/portfolios/{port_b['id']}/holdings",
            json={"ticker": "000660", "name": "SK하이닉스", "quantity": 5, "avg_price": 120000},
            headers=_auth_headers(token),
        )

        resp_a = await client.get(f"/portfolios/{port_a['id']}/holdings", headers=_auth_headers(token))
        resp_b = await client.get(f"/portfolios/{port_b['id']}/holdings", headers=_auth_headers(token))

        tickers_a = {h["ticker"] for h in resp_a.json()}
        tickers_b = {h["ticker"] for h in resp_b.json()}

        assert tickers_a == {"005930"}
        assert tickers_b == {"000660"}

    async def test_holdings_isolated_between_users(self, client: AsyncClient) -> None:
        """User A cannot see User B's holdings."""
        token_a = await _register_and_get_token(client, "multi2a@example.com")
        token_b = await _register_and_get_token(client, "multi2b@example.com")

        port_a = (await client.post("/portfolios", json={"name": "A"}, headers=_auth_headers(token_a))).json()
        await client.post(
            f"/portfolios/{port_a['id']}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
            headers=_auth_headers(token_a),
        )

        # User B attempts to access User A's portfolio — server returns 403 or 404
        resp = await client.get(f"/portfolios/{port_a['id']}/holdings", headers=_auth_headers(token_b))
        assert resp.status_code in (403, 404)

    async def test_multiple_portfolios_all_visible(self, client: AsyncClient) -> None:
        """All portfolios for a user are returned in GET /portfolios."""
        token = await _register_and_get_token(client, "multi3@example.com")
        for name in ["Alpha", "Beta", "Gamma"]:
            await client.post("/portfolios", json={"name": name}, headers=_auth_headers(token))

        resp = await client.get("/portfolios", headers=_auth_headers(token))
        names = {p["name"] for p in resp.json()}
        assert {"Alpha", "Beta", "Gamma"} <= names

    async def test_holding_count_correct_across_portfolios(self, client: AsyncClient) -> None:
        """Total holding count across two portfolios is accurate."""
        token = await _register_and_get_token(client, "multi4@example.com")
        for name in ["P1", "P2"]:
            port = (await client.post("/portfolios", json={"name": name}, headers=_auth_headers(token))).json()
            for i in range(2):
                await client.post(
                    f"/portfolios/{port['id']}/holdings",
                    json={"ticker": f"00593{i}", "name": f"종목{i}", "quantity": 1, "avg_price": 10000},
                    headers=_auth_headers(token),
                )

        # Fetch both portfolios and count total holdings
        portfolios = (await client.get("/portfolios", headers=_auth_headers(token))).json()
        total = 0
        for p in portfolios:
            h = await client.get(f"/portfolios/{p['id']}/holdings", headers=_auth_headers(token))
            total += len(h.json())
        assert total == 4
