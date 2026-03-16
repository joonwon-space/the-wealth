"""Portfolio rename API test."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestPortfolioRename:
    async def test_rename(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={"email": "rename@test.com", "password": "Test1234!"},
        )
        resp = await client.post(
            "/auth/login",
            json={"email": "rename@test.com", "password": "Test1234!"},
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post(
            "/portfolios", json={"name": "Old Name"}, headers=headers
        )
        pid = create.json()["id"]

        resp = await client.patch(
            f"/portfolios/{pid}",
            json={"name": "New Name"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    async def test_rename_empty_rejected(self, client: AsyncClient) -> None:
        await client.post(
            "/auth/register",
            json={"email": "rename2@test.com", "password": "Test1234!"},
        )
        resp = await client.post(
            "/auth/login",
            json={"email": "rename2@test.com", "password": "Test1234!"},
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post(
            "/portfolios", json={"name": "Test"}, headers=headers
        )
        pid = create.json()["id"]

        resp = await client.patch(
            f"/portfolios/{pid}",
            json={"name": ""},
            headers=headers,
        )
        assert resp.status_code == 422
