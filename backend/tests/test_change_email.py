"""Tests for POST /users/me/change-email endpoint."""

import pytest
from httpx import AsyncClient

TEST_EMAIL = "email_change@example.com"
TEST_EMAIL_2 = "email_change2@example.com"
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
class TestChangeEmail:
    async def test_change_email_success(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.post(
            "/users/me/change-email",
            json={
                "new_email": "new_email@example.com",
                "current_password": TEST_PASSWORD,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email changed successfully"

    async def test_change_email_wrong_password(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.post(
            "/users/me/change-email",
            json={
                "new_email": "another@example.com",
                "current_password": "WrongPassword!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["error"]["message"].lower()

    async def test_change_email_duplicate(self, client: AsyncClient) -> None:
        # Register a second user with the target email
        await _register_and_login(client, TEST_EMAIL_2, TEST_PASSWORD)
        # First user tries to change to the second user's email
        token = await _register_and_login(client, TEST_EMAIL, TEST_PASSWORD)
        resp = await client.post(
            "/users/me/change-email",
            json={
                "new_email": TEST_EMAIL_2,
                "current_password": TEST_PASSWORD,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
        assert "already" in resp.json()["error"]["message"].lower()

    async def test_change_email_unauthorized(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/users/me/change-email",
            json={"new_email": "x@x.com", "current_password": TEST_PASSWORD},
        )
        assert resp.status_code == 401
