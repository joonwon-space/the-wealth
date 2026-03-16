"""대시보드 summary API 테스트."""
from __future__ import annotations


import pytest
from httpx import AsyncClient


async def _setup_user_with_holdings(client: AsyncClient) -> str:
    """Register, login, create portfolio with a holding. Return access token."""
    await client.post("/auth/register", json={"email": "dash@example.com", "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": "dash@example.com", "password": "Test1234!"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    port = await client.post("/portfolios", json={"name": "test"}, headers=headers)
    pid = port.json()["id"]

    await client.post(
        f"/portfolios/{pid}/holdings",
        json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
        headers=headers,
    )
    return token


@pytest.mark.integration
class TestDashboardSummary:
    async def test_empty_portfolio(self, client: AsyncClient) -> None:
        """포트폴리오가 없으면 모든 값이 0."""
        await client.post("/auth/register", json={"email": "empty@example.com", "password": "Test1234!"})
        resp = await client.post("/auth/login", json={"email": "empty@example.com", "password": "Test1234!"})
        token = resp.json()["access_token"]

        resp = await client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["total_asset"]) == 0
        assert float(data["total_invested"]) == 0
        assert data["holdings"] == []
        assert data["allocation"] == []

    async def test_summary_without_kis_credentials(self, client: AsyncClient) -> None:
        """KIS 자격증명 없으면 현재가 없이 원금 기준으로 계산."""
        token = await _setup_user_with_holdings(client)

        resp = await client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        # 현재가 없으므로 total_asset = total_invested = 10 * 70000 = 700000
        assert float(data["total_invested"]) == 700000
        assert float(data["total_asset"]) == 700000
        assert len(data["holdings"]) == 1
        assert data["holdings"][0]["current_price"] is None

    async def test_unauthenticated(self, client: AsyncClient) -> None:
        """인증 없이 접근 불가."""
        resp = await client.get("/dashboard/summary")
        assert resp.status_code in (401, 403)
