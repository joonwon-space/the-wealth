"""인증 API 단위 테스트 (register, login, refresh)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "SecurePass123!"


@pytest.mark.integration
class TestRegister:
    async def test_register_success(self, client: AsyncClient) -> None:
        resp = await client.post("/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == TEST_EMAIL
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        # First registration
        await client.post("/auth/register", json={
            "email": "dup@example.com",
            "password": TEST_PASSWORD,
        })
        # Duplicate
        resp = await client.post("/auth/register", json={
            "email": "dup@example.com",
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 400

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        resp = await client.post("/auth/register", json={
            "email": "not-an-email",
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 422


@pytest.mark.integration
class TestLogin:
    async def test_login_success(self, client: AsyncClient) -> None:
        # Register first
        await client.post("/auth/register", json={
            "email": "login@example.com",
            "password": TEST_PASSWORD,
        })
        resp = await client.post("/auth/login", json={
            "email": "login@example.com",
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        await client.post("/auth/register", json={
            "email": "wrong@example.com",
            "password": TEST_PASSWORD,
        })
        resp = await client.post("/auth/login", json={
            "email": "wrong@example.com",
            "password": "WrongPass999!",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        resp = await client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 401


@pytest.mark.integration
class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient) -> None:
        await client.post("/auth/register", json={
            "email": "refresh@example.com",
            "password": TEST_PASSWORD,
        })
        login_resp = await client.post("/auth/login", json={
            "email": "refresh@example.com",
            "password": TEST_PASSWORD,
        })
        refresh_token = login_resp.json()["refresh_token"]

        resp = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient) -> None:
        resp = await client.post("/auth/refresh", json={
            "refresh_token": "invalid.token.here",
        })
        assert resp.status_code == 401
