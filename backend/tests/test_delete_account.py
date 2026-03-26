"""Tests for DELETE /users/me endpoint."""

import pytest
from httpx import AsyncClient

TEST_EMAIL = "delete_me@example.com"
TEST_PASSWORD = "SecurePass123!"


async def _register_and_login(client: AsyncClient, email: str, password: str) -> str:
    """Register a user and return the access token."""
    await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    return resp.json()["access_token"]


@pytest.mark.integration
class TestDeleteAccount:
    async def test_delete_account_success(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.request(
            "DELETE",
            "/users/me",
            json={"current_password": TEST_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Account deleted successfully"

    async def test_delete_account_wrong_password(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.request(
            "DELETE",
            "/users/me",
            json={"current_password": "WrongPassword!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["error"]["message"].lower()

    async def test_delete_account_user_no_longer_exists(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        # Delete the account
        await client.request(
            "DELETE",
            "/users/me",
            json={"current_password": TEST_PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Re-registering with same email should work (account is gone)
        resp = await client.post(
            "/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        assert resp.status_code == 201

    async def test_delete_account_unauthorized(self, client: AsyncClient) -> None:
        resp = await client.request(
            "DELETE",
            "/users/me",
            json={"current_password": TEST_PASSWORD},
        )
        assert resp.status_code == 401
