"""Soft delete tests for transactions."""

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, email: str) -> tuple[str, int]:
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
        json={"name": "soft delete test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, port.json()["id"]


@pytest.mark.integration
class TestSoftDelete:
    async def test_delete_hides_transaction_from_list(self, client: AsyncClient) -> None:
        token, pid = await _setup(client, "sd1@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Create a transaction
        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 10, "price": 70000},
            headers=headers,
        )
        assert resp.status_code == 201
        txn_id = resp.json()["id"]

        # Verify it appears in list
        list_resp = await client.get(f"/portfolios/{pid}/transactions", headers=headers)
        assert list_resp.status_code == 200
        ids = [t["id"] for t in list_resp.json()]
        assert txn_id in ids

        # Soft delete
        del_resp = await client.delete(f"/portfolios/transactions/{txn_id}", headers=headers)
        assert del_resp.status_code == 204

        # Verify it no longer appears in list
        list_resp2 = await client.get(f"/portfolios/{pid}/transactions", headers=headers)
        assert list_resp2.status_code == 200
        ids2 = [t["id"] for t in list_resp2.json()]
        assert txn_id not in ids2

    async def test_double_delete_returns_404(self, client: AsyncClient) -> None:
        token, pid = await _setup(client, "sd2@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "AAPL", "type": "BUY", "quantity": 5, "price": 180},
            headers=headers,
        )
        assert resp.status_code == 201
        txn_id = resp.json()["id"]

        # First delete — should succeed
        del1 = await client.delete(f"/portfolios/transactions/{txn_id}", headers=headers)
        assert del1.status_code == 204

        # Second delete — should return 404 since already soft-deleted
        del2 = await client.delete(f"/portfolios/transactions/{txn_id}", headers=headers)
        assert del2.status_code == 404

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient) -> None:
        token, _ = await _setup(client, "sd3@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.delete("/portfolios/transactions/999999", headers=headers)
        assert resp.status_code == 404
