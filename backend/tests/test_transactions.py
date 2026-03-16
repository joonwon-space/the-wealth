"""Transaction API tests (list + create, BUY/SELL validation, auth)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, email: str) -> tuple[str, int]:
    """Register, login, create portfolio. Return (token, portfolio_id)."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    port = await client.post("/portfolios", json={"name": "txn test"}, headers=headers)
    return token, port.json()["id"]


@pytest.mark.integration
class TestTransactionAPI:
    async def test_create_buy(self, client: AsyncClient) -> None:
        token, pid = await _setup(client, "txn1@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 10, "price": 70000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "BUY"
        assert data["ticker"] == "005930"

    async def test_create_sell(self, client: AsyncClient) -> None:
        token, pid = await _setup(client, "txn2@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "SELL", "quantity": 5, "price": 72000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["type"] == "SELL"

    async def test_invalid_type(self, client: AsyncClient) -> None:
        token, pid = await _setup(client, "txn3@test.com")
        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "INVALID", "quantity": 1, "price": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_list_transactions(self, client: AsyncClient) -> None:
        token, pid = await _setup(client, "txn4@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 10, "price": 70000},
            headers=headers,
        )
        resp = await client.get(f"/portfolios/{pid}/transactions", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/portfolios/1/transactions")
        assert resp.status_code in (401, 403)

    async def test_nonexistent_portfolio(self, client: AsyncClient) -> None:
        token, _ = await _setup(client, "txn5@test.com")
        resp = await client.post(
            "/portfolios/99999/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 1, "price": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
