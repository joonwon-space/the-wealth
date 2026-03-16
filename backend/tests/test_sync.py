"""KIS 계좌 동기화 API 테스트."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


@pytest.mark.integration
class TestSyncAPI:
    async def test_sync_without_kis_credentials(self, client: AsyncClient) -> None:
        """KIS 자격증명이 없으면 400 반환."""
        token = await _register_login(client, "sync1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        port = await client.post("/portfolios", json={"name": "sync test"}, headers=headers)
        pid = port.json()["id"]

        resp = await client.post(f"/sync/{pid}", headers=headers)
        assert resp.status_code == 400
        assert "kis account" in resp.json()["detail"].lower() or "credentials" in resp.json()["detail"].lower()

    async def test_sync_nonexistent_portfolio(self, client: AsyncClient) -> None:
        """존재하지 않는 포트폴리오 동기화 시 404."""
        token = await _register_login(client, "sync2@example.com")
        resp = await client.post(
            "/sync/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_sync_unauthenticated(self, client: AsyncClient) -> None:
        """인증 없이 접근 불가."""
        resp = await client.post("/sync/1")
        assert resp.status_code in (401, 403)

    async def test_get_sync_logs_empty(self, client: AsyncClient) -> None:
        """동기화 이력 없으면 빈 리스트."""
        token = await _register_login(client, "sync3@example.com")
        resp = await client.get("/sync/logs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []
