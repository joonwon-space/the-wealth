"""Pagination max limit cap tests — transactions and sync_logs."""

import pytest
from httpx import AsyncClient


async def _auth_and_portfolio(client: AsyncClient, email: str) -> tuple[str, int]:
    reg = await client.post(
        "/auth/register", json={"email": email, "password": "Test1234!"}
    )
    if reg.status_code == 429:
        pytest.skip("Rate limit hit — run individually")
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    if login.status_code == 429:
        pytest.skip("Rate limit hit — run individually")
    token = login.json()["access_token"]
    port = await client.post(
        "/portfolios",
        json={"name": "pagination test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, port.json()["id"]


@pytest.mark.integration
class TestPaginationCap:
    async def test_transactions_limit_default(self, client: AsyncClient) -> None:
        token, pid = await _auth_and_portfolio(client, "pgcap1@test.com")
        resp = await client.get(
            f"/portfolios/{pid}/transactions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_transactions_limit_at_max(self, client: AsyncClient) -> None:
        token, pid = await _auth_and_portfolio(client, "pgcap2@test.com")
        resp = await client.get(
            f"/portfolios/{pid}/transactions?limit=100",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_transactions_limit_over_max_rejected(self, client: AsyncClient) -> None:
        token, pid = await _auth_and_portfolio(client, "pgcap3@test.com")
        resp = await client.get(
            f"/portfolios/{pid}/transactions?limit=200",
            headers={"Authorization": f"Bearer {token}"},
        )
        # FastAPI Query(le=100) returns 422 for out-of-range values
        assert resp.status_code == 422

    async def test_transactions_limit_zero_rejected(self, client: AsyncClient) -> None:
        token, pid = await _auth_and_portfolio(client, "pgcap4@test.com")
        resp = await client.get(
            f"/portfolios/{pid}/transactions?limit=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
