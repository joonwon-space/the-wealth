"""Holdings-with-prices API test."""

import pytest
from httpx import AsyncClient


async def _setup_with_holding(client: AsyncClient, email: str) -> tuple[str, int]:
    """Register, login, create portfolio + holding. Return (token, portfolio_id)."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    port = await client.post(
        "/portfolios", json={"name": "price test"}, headers=headers
    )
    pid = port.json()["id"]

    await client.post(
        f"/portfolios/{pid}/holdings",
        json={
            "ticker": "005930",
            "name": "Samsung",
            "quantity": 10,
            "avg_price": 70000,
        },
        headers=headers,
    )
    return token, pid


@pytest.mark.integration
class TestHoldingsWithPrices:
    async def test_returns_holdings_without_kis_account(
        self, client: AsyncClient
    ) -> None:
        """No KIS account linked → holdings returned with null prices."""
        token, pid = await _setup_with_holding(client, "hp1@test.com")
        resp = await client.get(
            f"/portfolios/{pid}/holdings/with-prices",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "005930"
        assert data[0]["current_price"] is None
        assert data[0]["pnl_amount"] is None

    async def test_empty_portfolio(self, client: AsyncClient) -> None:
        """Empty portfolio → empty list."""
        await client.post(
            "/auth/register", json={"email": "hp2@test.com", "password": "Test1234!"}
        )
        resp = await client.post(
            "/auth/login", json={"email": "hp2@test.com", "password": "Test1234!"}
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        port = await client.post("/portfolios", json={"name": "empty"}, headers=headers)
        pid = port.json()["id"]

        resp = await client.get(
            f"/portfolios/{pid}/holdings/with-prices", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/portfolios/1/holdings/with-prices")
        assert resp.status_code in (401, 403)
