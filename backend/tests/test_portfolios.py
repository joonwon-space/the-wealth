"""포트폴리오 CRUD API 통합 테스트."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_and_get_token(client: AsyncClient, email: str = "port@example.com") -> str:
    """Helper: register user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
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
            json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
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
            json={"ticker": "005930", "name": "삼성전자", "quantity": 5, "avg_price": 65000},
            headers=_auth_headers(token),
        )
        resp = await client.get(f"/portfolios/{pid}/holdings", headers=_auth_headers(token))
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
            json={"ticker": "035720", "name": "카카오", "quantity": 20, "avg_price": 50000},
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
            json={"ticker": "000660", "name": "SK하이닉스", "quantity": 15, "avg_price": 120000},
            headers=_auth_headers(token),
        )
        hid = hold.json()["id"]

        resp = await client.delete(f"/portfolios/holdings/{hid}", headers=_auth_headers(token))
        assert resp.status_code == 204
