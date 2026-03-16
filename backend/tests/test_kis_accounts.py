"""KIS account CRUD API tests."""

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register", json={"email": email, "password": "Test1234!"}
    )
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


@pytest.mark.integration
class TestKisAccountCRUD:
    async def test_add_account(self, client: AsyncClient) -> None:
        token = await _login(client, "kis1@test.com")
        resp = await client.post(
            "/users/kis-accounts",
            json={
                "label": "Test",
                "account_no": "12345678",
                "acnt_prdt_cd": "01",
                "app_key": "testkey",
                "app_secret": "testsecret",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["label"] == "Test"
        assert resp.json()["account_no"] == "12345678"

    async def test_list_accounts(self, client: AsyncClient) -> None:
        token = await _login(client, "kis2@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post(
            "/users/kis-accounts",
            json={
                "label": "A",
                "account_no": "11111111",
                "app_key": "k",
                "app_secret": "s",
            },
            headers=headers,
        )
        resp = await client.get("/users/kis-accounts", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_label(self, client: AsyncClient) -> None:
        token = await _login(client, "kis3@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        create = await client.post(
            "/users/kis-accounts",
            json={
                "label": "Old",
                "account_no": "22222222",
                "app_key": "k",
                "app_secret": "s",
            },
            headers=headers,
        )
        aid = create.json()["id"]
        resp = await client.patch(
            f"/users/kis-accounts/{aid}",
            json={"label": "New"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "New"

    async def test_delete_account(self, client: AsyncClient) -> None:
        token = await _login(client, "kis4@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        create = await client.post(
            "/users/kis-accounts",
            json={
                "label": "Del",
                "account_no": "33333333",
                "app_key": "k",
                "app_secret": "s",
            },
            headers=headers,
        )
        aid = create.json()["id"]
        resp = await client.delete(
            f"/users/kis-accounts/{aid}", headers=headers
        )
        assert resp.status_code == 204

    async def test_duplicate_rejected(self, client: AsyncClient) -> None:
        token = await _login(client, "kis5@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        body = {
            "label": "Dup",
            "account_no": "44444444",
            "acnt_prdt_cd": "01",
            "app_key": "k",
            "app_secret": "s",
        }
        await client.post("/users/kis-accounts", json=body, headers=headers)
        resp = await client.post(
            "/users/kis-accounts", json=body, headers=headers
        )
        assert resp.status_code == 409

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/users/kis-accounts")
        assert resp.status_code in (401, 403)
