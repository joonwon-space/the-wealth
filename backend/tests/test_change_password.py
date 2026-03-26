"""Tests for POST /users/me/change-password endpoint."""

import pytest
from httpx import AsyncClient

TEST_EMAIL = "pw_change@example.com"
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
class TestChangePassword:
    async def test_change_password_success(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.post(
            "/users/me/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "NewPass456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password changed successfully"

    async def test_change_password_wrong_current(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.post(
            "/users/me/change-password",
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewPass456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["error"]["message"].lower()

    async def test_change_password_too_short(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.post(
            "/users/me/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "short",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_change_password_unauthorized(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/users/me/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "NewPass456!",
            },
        )
        assert resp.status_code == 401
