"""Tests for GET /users/me and PATCH /users/me endpoints."""

import pytest
from httpx import AsyncClient

TEST_EMAIL = "me_test@example.com"
TEST_PASSWORD = "SecurePass123!"


async def _register_and_login(client: AsyncClient) -> str:
    """Register a user and return the access token."""
    await client.post(
        "/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    return resp.json()["access_token"]


@pytest.mark.integration
class TestGetMe:
    async def test_get_me_returns_email_and_no_name(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == TEST_EMAIL
        assert data["name"] is None
        assert "id" in data

    async def test_get_me_unauthorized(self, client: AsyncClient) -> None:
        resp = await client.get("/users/me")
        assert resp.status_code == 401


@pytest.mark.integration
class TestPatchMe:
    async def test_patch_me_set_name(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        resp = await client.patch(
            "/users/me",
            json={"name": "테스트 사용자"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "테스트 사용자"
        assert data["email"] == TEST_EMAIL

    async def test_patch_me_clear_name(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        # Set name first
        await client.patch(
            "/users/me",
            json={"name": "Some Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Clear name with empty string
        resp = await client.patch(
            "/users/me",
            json={"name": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] is None

    async def test_patch_me_name_persists_on_get(self, client: AsyncClient) -> None:
        token = await _register_and_login(client)
        await client.patch(
            "/users/me",
            json={"name": "Persisted Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Persisted Name"

    async def test_patch_me_unauthorized(self, client: AsyncClient) -> None:
        resp = await client.patch("/users/me", json={"name": "test"})
        assert resp.status_code == 401
