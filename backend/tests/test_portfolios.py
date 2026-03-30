"""포트폴리오 CRUD API 통합 테스트."""

import pytest
from httpx import AsyncClient


async def _register_and_get_token(
    client: AsyncClient, email: str = "port@example.com"
) -> str:
    """Helper: register user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestPortfolios:
    async def test_create_portfolio(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "create@example.com")
        resp = await client.post(
            "/portfolios",
            json={"name": "내 포트폴리오", "currency": "KRW"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "내 포트폴리오"
        assert data["currency"] == "KRW"
        assert "id" in data

    async def test_list_portfolios(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "list@example.com")
        await client.post(
            "/portfolios",
            json={"name": "포트폴리오 A"},
            headers=_auth_headers(token),
        )
        resp = await client.get("/portfolios", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    async def test_delete_portfolio(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "del@example.com")
        create_resp = await client.post(
            "/portfolios",
            json={"name": "삭제용"},
            headers=_auth_headers(token),
        )
        pid = create_resp.json()["id"]
        resp = await client.delete(f"/portfolios/{pid}", headers=_auth_headers(token))
        assert resp.status_code == 204

    async def test_delete_portfolio_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "del404@example.com")
        resp = await client.delete("/portfolios/99999", headers=_auth_headers(token))
        assert resp.status_code == 404

    async def test_unauthenticated_access(self, client: AsyncClient) -> None:
        resp = await client.get("/portfolios")
        assert resp.status_code in (401, 403)

    async def test_patch_portfolio_target_value(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "patch_target@example.com")
        create_resp = await client.post(
            "/portfolios",
            json={"name": "목표 테스트"},
            headers=_auth_headers(token),
        )
        pid = create_resp.json()["id"]

        # Set target_value
        resp = await client.patch(
            f"/portfolios/{pid}",
            json={"target_value": 10000000},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_value"] == 10000000

    async def test_patch_portfolio_clear_target_value(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "patch_clear@example.com")
        create_resp = await client.post(
            "/portfolios",
            json={"name": "목표 초기화 테스트"},
            headers=_auth_headers(token),
        )
        pid = create_resp.json()["id"]

        # Set target_value first
        await client.patch(
            f"/portfolios/{pid}",
            json={"target_value": 5000000},
            headers=_auth_headers(token),
        )

        # Clear target_value
        resp = await client.patch(
            f"/portfolios/{pid}",
            json={"target_value": None},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["target_value"] is None

    async def test_patch_portfolio_name_only(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "patch_name@example.com")
        create_resp = await client.post(
            "/portfolios",
            json={"name": "이름 변경 전"},
            headers=_auth_headers(token),
        )
        pid = create_resp.json()["id"]

        resp = await client.patch(
            f"/portfolios/{pid}",
            json={"name": "이름 변경 후"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "이름 변경 후"

    async def test_patch_portfolio_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "patch404@example.com")
        resp = await client.patch(
            "/portfolios/99999",
            json={"name": "없음"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestHoldings:
    async def test_add_holding(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "hold@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "종목 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        resp = await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": 10,
                "avg_price": 70000,
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["name"] == "삼성전자"

    async def test_list_holdings(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "listh@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "목록 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": 5,
                "avg_price": 65000,
            },
            headers=_auth_headers(token),
        )
        resp = await client.get(
            f"/portfolios/{pid}/holdings", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_holding(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "upd@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "수정 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        hold = await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "035720",
                "name": "카카오",
                "quantity": 20,
                "avg_price": 50000,
            },
            headers=_auth_headers(token),
        )
        hid = hold.json()["id"]

        resp = await client.patch(
            f"/portfolios/holdings/{hid}",
            json={"quantity": 30},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert float(resp.json()["quantity"]) == 30

    async def test_delete_holding(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "delh@example.com")
        port = await client.post(
            "/portfolios",
            json={"name": "삭제 테스트"},
            headers=_auth_headers(token),
        )
        pid = port.json()["id"]

        hold = await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "000660",
                "name": "SK하이닉스",
                "quantity": 15,
                "avg_price": 120000,
            },
            headers=_auth_headers(token),
        )
        hid = hold.json()["id"]

        resp = await client.delete(
            f"/portfolios/holdings/{hid}", headers=_auth_headers(token)
        )
        assert resp.status_code == 204


@pytest.mark.integration
class TestMultiplePortfoliosHoldings:
    """Verify holdings are correctly scoped to their portfolio and user."""

    async def test_holdings_isolated_between_portfolios(self, client: AsyncClient) -> None:
        """Holdings in portfolio A are not visible in portfolio B."""
        token = await _register_and_get_token(client, "multi1@example.com")
        port_a = (await client.post("/portfolios", json={"name": "A"}, headers=_auth_headers(token))).json()
        port_b = (await client.post("/portfolios", json={"name": "B"}, headers=_auth_headers(token))).json()

        await client.post(
            f"/portfolios/{port_a['id']}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
            headers=_auth_headers(token),
        )
        await client.post(
            f"/portfolios/{port_b['id']}/holdings",
            json={"ticker": "000660", "name": "SK하이닉스", "quantity": 5, "avg_price": 120000},
            headers=_auth_headers(token),
        )

        resp_a = await client.get(f"/portfolios/{port_a['id']}/holdings", headers=_auth_headers(token))
        resp_b = await client.get(f"/portfolios/{port_b['id']}/holdings", headers=_auth_headers(token))

        tickers_a = {h["ticker"] for h in resp_a.json()}
        tickers_b = {h["ticker"] for h in resp_b.json()}

        assert tickers_a == {"005930"}
        assert tickers_b == {"000660"}

    async def test_holdings_isolated_between_users(self, client: AsyncClient) -> None:
        """User A cannot see User B's holdings."""
        token_a = await _register_and_get_token(client, "multi2a@example.com")
        token_b = await _register_and_get_token(client, "multi2b@example.com")

        port_a = (await client.post("/portfolios", json={"name": "A"}, headers=_auth_headers(token_a))).json()
        await client.post(
            f"/portfolios/{port_a['id']}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 10, "avg_price": 70000},
            headers=_auth_headers(token_a),
        )

        # User B attempts to access User A's portfolio — server returns 403 or 404
        resp = await client.get(f"/portfolios/{port_a['id']}/holdings", headers=_auth_headers(token_b))
        assert resp.status_code in (403, 404)

    async def test_multiple_portfolios_all_visible(self, client: AsyncClient) -> None:
        """All portfolios for a user are returned in GET /portfolios."""
        token = await _register_and_get_token(client, "multi3@example.com")
        for name in ["Alpha", "Beta", "Gamma"]:
            await client.post("/portfolios", json={"name": name}, headers=_auth_headers(token))

        resp = await client.get("/portfolios", headers=_auth_headers(token))
        names = {p["name"] for p in resp.json()}
        assert {"Alpha", "Beta", "Gamma"} <= names

    async def test_holding_count_correct_across_portfolios(self, client: AsyncClient) -> None:
        """Total holding count across two portfolios is accurate."""
        token = await _register_and_get_token(client, "multi4@example.com")
        for name in ["P1", "P2"]:
            port = (await client.post("/portfolios", json={"name": name}, headers=_auth_headers(token))).json()
            for i in range(2):
                await client.post(
                    f"/portfolios/{port['id']}/holdings",
                    json={"ticker": f"00593{i}", "name": f"종목{i}", "quantity": 1, "avg_price": 10000},
                    headers=_auth_headers(token),
                )

        # Fetch both portfolios and count total holdings
        portfolios = (await client.get("/portfolios", headers=_auth_headers(token))).json()
        total = 0
        for p in portfolios:
            h = await client.get(f"/portfolios/{p['id']}/holdings", headers=_auth_headers(token))
            total += len(h.json())
        assert total == 4


@pytest.mark.integration
class TestPortfolioUpdate:
    async def test_update_portfolio_name(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "upd1@example.com")
        port = await client.post(
            "/portfolios", json={"name": "Old Name"}, headers=_auth_headers(token)
        )
        pid = port.json()["id"]

        resp = await client.patch(
            f"/portfolios/{pid}",
            json={"name": "New Name"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    async def test_update_portfolio_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "upd2@example.com")
        resp = await client.patch(
            "/portfolios/99999",
            json={"name": "Doesn't Matter"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_update_other_user_portfolio_is_forbidden(
        self, client: AsyncClient
    ) -> None:
        token_a = await _register_and_get_token(client, "upd3a@example.com")
        token_b = await _register_and_get_token(client, "upd3b@example.com")

        port = await client.post(
            "/portfolios", json={"name": "Owner's Portfolio"}, headers=_auth_headers(token_a)
        )
        pid = port.json()["id"]

        resp = await client.patch(
            f"/portfolios/{pid}",
            json={"name": "Stolen"},
            headers=_auth_headers(token_b),
        )
        assert resp.status_code in (403, 404)


@pytest.mark.integration
class TestHoldingEdgeCases:
    async def test_add_holding_to_nonexistent_portfolio(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "hld1@example.com")
        resp = await client.post(
            "/portfolios/99999/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 1, "avg_price": 70000},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_add_holding_to_other_user_portfolio(
        self, client: AsyncClient
    ) -> None:
        token_a = await _register_and_get_token(client, "hld2a@example.com")
        token_b = await _register_and_get_token(client, "hld2b@example.com")

        port = await client.post(
            "/portfolios", json={"name": "P"}, headers=_auth_headers(token_a)
        )
        pid = port.json()["id"]

        resp = await client.post(
            f"/portfolios/{pid}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 1, "avg_price": 70000},
            headers=_auth_headers(token_b),
        )
        assert resp.status_code in (403, 404)

    async def test_update_holding_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "hld3@example.com")
        resp = await client.patch(
            "/portfolios/holdings/99999",
            json={"quantity": 5},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_delete_holding_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "hld4@example.com")
        resp = await client.delete(
            "/portfolios/holdings/99999",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_list_holdings_nonexistent_portfolio(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "hld5@example.com")
        resp = await client.get(
            "/portfolios/99999/holdings", headers=_auth_headers(token)
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestTransactionsCRUD:
    async def _create_portfolio(self, client: AsyncClient, token: str) -> int:
        resp = await client.post(
            "/portfolios", json={"name": "Txn Test"}, headers=_auth_headers(token)
        )
        return resp.json()["id"]

    async def test_create_transaction(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "txn1@example.com")
        pid = await self._create_portfolio(client, token)

        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 10, "price": 70000},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["type"] == "BUY"
        assert float(data["quantity"]) == 10

    async def test_list_transactions_empty(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "txn2@example.com")
        pid = await self._create_portfolio(client, token)

        resp = await client.get(
            f"/portfolios/{pid}/transactions", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_transactions_after_create(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "txn3@example.com")
        pid = await self._create_portfolio(client, token)

        await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 5, "price": 65000},
            headers=_auth_headers(token),
        )
        resp = await client.get(
            f"/portfolios/{pid}/transactions", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_delete_transaction(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "txn4@example.com")
        pid = await self._create_portfolio(client, token)

        txn = await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "000660", "type": "SELL", "quantity": 3, "price": 130000},
            headers=_auth_headers(token),
        )
        tid = txn.json()["id"]

        resp = await client.delete(
            f"/portfolios/transactions/{tid}", headers=_auth_headers(token)
        )
        assert resp.status_code == 204

        # Deleted transaction should not appear in listing (soft delete)
        listing = await client.get(
            f"/portfolios/{pid}/transactions", headers=_auth_headers(token)
        )
        ids = [t["id"] for t in listing.json()]
        assert tid not in ids

    async def test_delete_nonexistent_transaction(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "txn5@example.com")
        resp = await client.delete(
            "/portfolios/transactions/99999", headers=_auth_headers(token)
        )
        assert resp.status_code == 404

    async def test_list_transactions_nonexistent_portfolio(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "txn6@example.com")
        resp = await client.get(
            "/portfolios/99999/transactions", headers=_auth_headers(token)
        )
        assert resp.status_code == 404

    async def test_create_transaction_with_traded_at(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "txn7@example.com")
        pid = await self._create_portfolio(client, token)

        resp = await client.post(
            f"/portfolios/{pid}/transactions",
            json={
                "ticker": "035720",
                "type": "BUY",
                "quantity": 2,
                "price": 50000,
                "traded_at": "2024-01-15T10:00:00",
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        assert "2024-01-15" in resp.json()["traded_at"]


@pytest.mark.integration
class TestHoldingsWithPrices:
    async def test_holdings_with_prices_empty_portfolio(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_get_token(client, "wp1@example.com")
        port = await client.post(
            "/portfolios", json={"name": "WP"}, headers=_auth_headers(token)
        )
        pid = port.json()["id"]

        resp = await client.get(
            f"/portfolios/{pid}/holdings/with-prices", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_holdings_with_prices_no_kis_account(
        self, client: AsyncClient
    ) -> None:
        """No KIS account → prices are None but holdings are returned."""
        token = await _register_and_get_token(client, "wp2@example.com")
        port = await client.post(
            "/portfolios", json={"name": "WP2"}, headers=_auth_headers(token)
        )
        pid = port.json()["id"]

        await client.post(
            f"/portfolios/{pid}/holdings",
            json={"ticker": "005930", "name": "삼성전자", "quantity": 5, "avg_price": 70000},
            headers=_auth_headers(token),
        )

        resp = await client.get(
            f"/portfolios/{pid}/holdings/with-prices", headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        # No KIS account → current_price is None
        assert items[0]["current_price"] is None

    async def test_holdings_with_prices_not_found(self, client: AsyncClient) -> None:
        token = await _register_and_get_token(client, "wp3@example.com")
        resp = await client.get(
            "/portfolios/99999/holdings/with-prices", headers=_auth_headers(token)
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestTransactionsPaginated:
    async def _setup(self, client: AsyncClient, email: str) -> tuple[str, int]:
        token = await _register_and_get_token(client, email)
        port = (await client.post("/portfolios", json={"name": "P"}, headers=_auth_headers(token))).json()
        return token, port["id"]

    async def _add_txn(self, client: AsyncClient, token: str, pid: int, ticker: str = "005930") -> None:
        await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": ticker, "type": "BUY", "quantity": 1, "price": 70000},
            headers=_auth_headers(token),
        )

    async def test_paginated_first_page_empty(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "paged_empty@example.com")
        resp = await client.get(
            f"/portfolios/{pid}/transactions/paginated",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    async def test_paginated_less_than_limit(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "paged_few@example.com")
        for _ in range(3):
            await self._add_txn(client, token, pid)
        resp = await client.get(
            f"/portfolios/{pid}/transactions/paginated",
            params={"limit": 20},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    async def test_paginated_has_more(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "paged_more@example.com")
        for _ in range(5):
            await self._add_txn(client, token, pid)
        resp = await client.get(
            f"/portfolios/{pid}/transactions/paginated",
            params={"limit": 3},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

    async def test_paginated_cursor_next_page(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "paged_cursor@example.com")
        for _ in range(5):
            await self._add_txn(client, token, pid)
        # First page
        resp1 = await client.get(
            f"/portfolios/{pid}/transactions/paginated",
            params={"limit": 3},
            headers=_auth_headers(token),
        )
        cursor = resp1.json()["next_cursor"]
        # Second page
        resp2 = await client.get(
            f"/portfolios/{pid}/transactions/paginated",
            params={"limit": 3, "cursor": cursor},
            headers=_auth_headers(token),
        )
        data2 = resp2.json()
        assert len(data2["items"]) == 2
        assert data2["has_more"] is False

    async def test_paginated_not_found(self, client: AsyncClient) -> None:
        token, _ = await self._setup(client, "paged404@example.com")
        resp = await client.get(
            "/portfolios/99999/transactions/paginated",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestBulkHoldings:
    """보유 종목 일괄 등록 API 테스트."""

    async def _setup(self, client: AsyncClient, email: str) -> tuple[str, int]:
        await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
        resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
        token = resp.json()["access_token"]
        port = await client.post(
            "/portfolios",
            json={"name": "Bulk Test Portfolio"},
            headers=_auth_headers(token),
        )
        return token, port.json()["id"]

    async def test_bulk_create_new_holdings(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "bulk_create@example.com")
        resp = await client.post(
            f"/portfolios/{pid}/holdings/bulk",
            json={
                "items": [
                    {"ticker": "005930", "name": "삼성전자", "quantity": "10", "avg_price": "70000"},
                    {"ticker": "AAPL", "name": "Apple", "quantity": "5", "avg_price": "150.00"},
                ]
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 2
        assert data["updated"] == 0
        assert data["errors"] == []

    async def test_bulk_upsert_existing_holding(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "bulk_upsert@example.com")
        # 첫 번째 등록
        await client.post(
            f"/portfolios/{pid}/holdings/bulk",
            json={
                "items": [
                    {"ticker": "005930", "name": "삼성전자", "quantity": "10", "avg_price": "70000"},
                ]
            },
            headers=_auth_headers(token),
        )
        # 추가 매수 (upsert)
        resp = await client.post(
            f"/portfolios/{pid}/holdings/bulk",
            json={
                "items": [
                    {"ticker": "005930", "name": "삼성전자", "quantity": "10", "avg_price": "80000"},
                ]
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 0
        assert data["updated"] == 1

        # 평단가 가중평균 확인: (10*70000 + 10*80000) / 20 = 75000
        holdings = await client.get(
            f"/portfolios/{pid}/holdings",
            headers=_auth_headers(token),
        )
        h = next(h for h in holdings.json() if h["ticker"] == "005930")
        assert float(h["avg_price"]) == pytest.approx(75000.0)
        assert float(h["quantity"]) == pytest.approx(20.0)

    async def test_bulk_not_found(self, client: AsyncClient) -> None:
        token, _ = await self._setup(client, "bulk_404@example.com")
        resp = await client.post(
            "/portfolios/99999/holdings/bulk",
            json={"items": [{"ticker": "005930", "name": "삼성전자", "quantity": "1", "avg_price": "70000"}]},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_bulk_forbidden_other_user(self, client: AsyncClient) -> None:
        token1, pid = await self._setup(client, "bulk_owner@example.com")
        # 다른 사용자
        await client.post("/auth/register", json={"email": "bulk_other@example.com", "password": "Test1234!"})
        resp2 = await client.post("/auth/login", json={"email": "bulk_other@example.com", "password": "Test1234!"})
        token2 = resp2.json()["access_token"]
        resp = await client.post(
            f"/portfolios/{pid}/holdings/bulk",
            json={"items": [{"ticker": "005930", "name": "삼성전자", "quantity": "1", "avg_price": "70000"}]},
            headers=_auth_headers(token2),
        )
        assert resp.status_code == 403

    async def test_bulk_empty_items_rejected(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "bulk_empty@example.com")
        resp = await client.post(
            f"/portfolios/{pid}/holdings/bulk",
            json={"items": []},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_bulk_invalid_ticker_rejected(self, client: AsyncClient) -> None:
        token, pid = await self._setup(client, "bulk_badticker@example.com")
        resp = await client.post(
            f"/portfolios/{pid}/holdings/bulk",
            json={
                "items": [
                    {"ticker": "INVALID_TICKER_TOO_LONG", "name": "Bad", "quantity": "1", "avg_price": "1000"},
                ]
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422
