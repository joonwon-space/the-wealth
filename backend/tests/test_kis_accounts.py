"""KIS account CRUD API tests."""

from unittest.mock import AsyncMock, patch

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

    async def test_add_account_response_fields(self, client: AsyncClient) -> None:
        """Response includes id, label, account_no, acnt_prdt_cd."""
        token = await _login(client, "kis7@test.com")
        resp = await client.post(
            "/users/kis-accounts",
            json={
                "label": "My Account",
                "account_no": "99999999",
                "acnt_prdt_cd": "01",
                "app_key": "key123",
                "app_secret": "secret123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["label"] == "My Account"
        assert data["account_no"] == "99999999"
        assert data["acnt_prdt_cd"] == "01"
        # app_key and app_secret should NOT be returned
        assert "app_key" not in data
        assert "app_secret" not in data

    async def test_list_accounts_returns_correct_fields(
        self, client: AsyncClient
    ) -> None:
        token = await _login(client, "kis8@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post(
            "/users/kis-accounts",
            json={"label": "L", "account_no": "88888888", "app_key": "k", "app_secret": "s"},
            headers=headers,
        )
        resp = await client.get("/users/kis-accounts", headers=headers)
        assert resp.status_code == 200
        accounts = resp.json()
        assert len(accounts) >= 1
        acct = accounts[0]
        assert "id" in acct
        assert "label" in acct
        assert "account_no" in acct
        assert "app_key" not in acct
        assert "app_secret" not in acct

    async def test_update_not_found_returns_404(self, client: AsyncClient) -> None:
        token = await _login(client, "kis9@test.com")
        resp = await client.patch(
            "/users/kis-accounts/99999",
            json={"label": "Nonexistent"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_update_other_user_account_returns_404(
        self, client: AsyncClient
    ) -> None:
        token_a = await _login(client, "kis10a@test.com")
        token_b = await _login(client, "kis10b@test.com")

        create = await client.post(
            "/users/kis-accounts",
            json={"label": "A", "account_no": "77777777", "app_key": "k", "app_secret": "s"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        aid = create.json()["id"]

        resp = await client.patch(
            f"/users/kis-accounts/{aid}",
            json={"label": "Stolen"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

    async def test_delete_not_found_returns_404(self, client: AsyncClient) -> None:
        token = await _login(client, "kis11@test.com")
        resp = await client.delete(
            "/users/kis-accounts/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_delete_other_user_account_returns_404(
        self, client: AsyncClient
    ) -> None:
        token_a = await _login(client, "kis12a@test.com")
        token_b = await _login(client, "kis12b@test.com")

        create = await client.post(
            "/users/kis-accounts",
            json={"label": "A", "account_no": "66666666", "app_key": "k", "app_secret": "s"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        aid = create.json()["id"]

        resp = await client.delete(
            f"/users/kis-accounts/{aid}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

    async def test_test_connection_success(self, client: AsyncClient) -> None:
        """Connection test returns success=True when KIS token obtained."""
        token = await _login(client, "kis13@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post(
            "/users/kis-accounts",
            json={"label": "T", "account_no": "55555555", "app_key": "k", "app_secret": "s"},
            headers=headers,
        )
        aid = create.json()["id"]

        with patch(
            "app.api.users.get_kis_access_token",
            new_callable=AsyncMock,
            return_value="fake_token",
        ):
            resp = await client.post(
                f"/users/kis-accounts/{aid}/test", headers=headers
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_test_connection_failure(self, client: AsyncClient) -> None:
        """Connection test returns success=False when KIS token fails."""
        token = await _login(client, "kis14@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post(
            "/users/kis-accounts",
            json={"label": "F", "account_no": "44444445", "app_key": "k", "app_secret": "s"},
            headers=headers,
        )
        aid = create.json()["id"]

        with patch(
            "app.api.users.get_kis_access_token",
            new_callable=AsyncMock,
            side_effect=RuntimeError("invalid credentials"),
        ):
            resp = await client.post(
                f"/users/kis-accounts/{aid}/test", headers=headers
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_test_connection_not_found(self, client: AsyncClient) -> None:
        """Test connection on non-existent account returns 404."""
        token = await _login(client, "kis15@test.com")
        resp = await client.post(
            "/users/kis-accounts/99999/test",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
