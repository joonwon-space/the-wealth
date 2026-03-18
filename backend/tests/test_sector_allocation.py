"""섹터 배분 API 통합 테스트 (정상 응답, 빈 포트폴리오, 매핑 없는 종목)."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "sector@example.com"
) -> str:
    """Helper: register user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio_with_holdings(
    client: AsyncClient, token: str, holdings: list[dict]
) -> int:
    port = await client.post(
        "/portfolios",
        json={"name": "섹터 테스트"},
        headers=_auth_headers(token),
    )
    pid = port.json()["id"]
    for h in holdings:
        await client.post(
            f"/portfolios/{pid}/holdings",
            json=h,
            headers=_auth_headers(token),
        )
    return pid


@pytest.mark.integration
class TestSectorAllocationNormal:
    async def test_sector_allocation_returns_200(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "sector_200@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        assert resp.status_code == 200

    async def test_sector_allocation_response_schema(self, client: AsyncClient) -> None:
        """Response items must have sector, value, weight fields."""
        token = await _register_and_get_token(client, "sector_schema@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        assert len(data) > 0
        item = data[0]
        assert "sector" in item
        assert "value" in item
        assert "weight" in item

    async def test_single_sector_weight_is_100(self, client: AsyncClient) -> None:
        """With only one sector, its weight should be 100.0%."""
        token = await _register_and_get_token(client, "sector_100pct@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [
                {"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
                {"ticker": "000660", "name": "SK하이닉스", "quantity": 5, "avg_price": 120000},
            ],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        # Both are IT sector
        assert len(data) == 1
        assert data[0]["sector"] == "IT"
        assert data[0]["weight"] == 100.0

    async def test_weights_sum_to_100(self, client: AsyncClient) -> None:
        """All weights should sum to approximately 100%."""
        token = await _register_and_get_token(client, "sector_sum@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [
                # IT sector
                {"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
                # 금융 sector
                {"ticker": "105560", "name": "KB금융", "quantity": 5, "avg_price": 50000},
                # 헬스케어 sector
                {"ticker": "068270", "name": "셀트리온", "quantity": 3, "avg_price": 200000},
            ],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        total_weight = sum(item["weight"] for item in data)
        assert abs(total_weight - 100.0) < 0.2  # Allow small rounding error

    async def test_value_equals_quantity_times_avg_price(self, client: AsyncClient) -> None:
        """Sector value should equal sum of (quantity * avg_price) for that sector's holdings."""
        token = await _register_and_get_token(client, "sector_value@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [{"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000}],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        it_sector = next(item for item in data if item["sector"] == "IT")
        assert it_sector["value"] == 10 * 70000

    async def test_sectors_sorted_by_value_descending(self, client: AsyncClient) -> None:
        """Sectors should be returned sorted by value descending."""
        token = await _register_and_get_token(client, "sector_sort@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [
                # IT: 10 * 70000 = 700000
                {"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
                # 금융: 5 * 50000 = 250000
                {"ticker": "105560", "name": "KB금융", "quantity": 5, "avg_price": 50000},
            ],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        values = [item["value"] for item in data]
        assert values == sorted(values, reverse=True)

    async def test_sector_allocation_across_multiple_portfolios(
        self, client: AsyncClient
    ) -> None:
        """Holdings from multiple portfolios are aggregated by sector."""
        token = await _register_and_get_token(client, "sector_multi@example.com")

        # Portfolio 1: IT
        port1 = await client.post(
            "/portfolios", json={"name": "포트1"}, headers=_auth_headers(token)
        )
        p1id = port1.json()["id"]
        await client.post(
            f"/portfolios/{p1id}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
            headers=_auth_headers(token),
        )

        # Portfolio 2: also IT
        port2 = await client.post(
            "/portfolios", json={"name": "포트2"}, headers=_auth_headers(token)
        )
        p2id = port2.json()["id"]
        await client.post(
            f"/portfolios/{p2id}/holdings",
            json={"ticker": "000660", "name": "SK하이닉스", "quantity": 5, "avg_price": 120000},
            headers=_auth_headers(token),
        )

        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        it_sector = next((item for item in data if item["sector"] == "IT"), None)
        assert it_sector is not None
        # Total IT value: 10*70000 + 5*120000 = 700000 + 600000 = 1300000
        assert it_sector["value"] == 1300000


@pytest.mark.integration
class TestSectorAllocationEmpty:
    async def test_no_portfolios_returns_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "sector_empty1@example.com")
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_portfolio_with_no_holdings_returns_empty(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "sector_empty2@example.com")
        await client.post(
            "/portfolios", json={"name": "빈 포트폴리오"}, headers=_auth_headers(token)
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_unauthenticated_denied(self, client: AsyncClient) -> None:
        resp = await client.get("/analytics/sector-allocation")
        assert resp.status_code in (401, 403)


@pytest.mark.integration
class TestSectorAllocationUnmappedTickers:
    async def test_unknown_ticker_falls_back_to_gita_sector(
        self, client: AsyncClient
    ) -> None:
        """Tickers not in sector_map should fall into '기타' sector."""
        token = await _register_and_get_token(client, "sector_other@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [
                {
                    "ticker": "ZZZZZ",  # Not in sector_map
                    "name": "미매핑 종목",
                    "quantity": 1,
                    "avg_price": 10000,
                }
            ],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        assert len(data) == 1
        assert data[0]["sector"] == "기타"

    async def test_mixed_known_and_unknown_tickers(self, client: AsyncClient) -> None:
        """Mix of known and unknown tickers should create separate sector entries."""
        token = await _register_and_get_token(client, "sector_mixed@example.com")
        await _create_portfolio_with_holdings(
            client,
            token,
            [
                {"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
                {"ticker": "ZZZZZ", "name": "미매핑 종목", "quantity": 1, "avg_price": 10000},
            ],
        )
        resp = await client.get("/analytics/sector-allocation", headers=_auth_headers(token))
        data = resp.json()
        sectors = {item["sector"] for item in data}
        assert "IT" in sectors
        assert "기타" in sectors
