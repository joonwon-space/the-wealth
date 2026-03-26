"""KIS 계좌 동기화 API 테스트."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


async def _add_kis_account(client: AsyncClient, token: str) -> dict:
    """Add a KIS account; return the response JSON."""
    resp = await client.post(
        "/users/kis-accounts",
        json={
            "label": "Test",
            "account_no": "12345678",
            "acnt_prdt_cd": "01",
            "app_key": "dummy_key",
            "app_secret": "dummy_secret",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


def _mock_kis_holdings() -> list:
    """Return a list of mock KisHolding objects."""
    from app.services.kis_account import KisHolding

    return [
        KisHolding(
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
            market="KRW",
        )
    ]


def _make_balance_raw_result() -> tuple:
    summary = {
        "dnca_tot_amt": "1000000",
        "tot_evlu_amt": "1100000",
        "scts_evlu_amt": "700000",
        "evlu_pfls_smtl_amt": "100000",
    }
    return summary, _mock_kis_holdings()


@pytest.mark.integration
class TestSyncAPI:
    async def test_sync_without_kis_credentials(self, client: AsyncClient) -> None:
        """KIS 자격증명이 없으면 400 반환."""
        token = await _register_login(client, "sync1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        port = await client.post(
            "/portfolios", json={"name": "sync test"}, headers=headers
        )
        pid = port.json()["id"]

        resp = await client.post(f"/sync/{pid}", headers=headers)
        assert resp.status_code == 400
        body = resp.json()
        # Support both legacy {"detail": ...} and new {"error": {"message": ...}} formats
        message = (
            body.get("error", {}).get("message", "")
            or str(body.get("detail", ""))
        ).lower()
        assert "kis account" in message or "credentials" in message

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
        """동기화 이력 없으면 빈 items 리스트."""
        token = await _register_login(client, "sync3@example.com")
        resp = await client.get(
            "/sync/logs", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["next_cursor"] is None
        assert data["has_more"] is False

    async def test_get_sync_logs_unauthenticated(self, client: AsyncClient) -> None:
        """인증 없이 sync logs 접근 불가."""
        resp = await client.get("/sync/logs")
        assert resp.status_code in (401, 403)

    async def test_balance_no_kis_account_returns_400(self, client: AsyncClient) -> None:
        """KIS 계좌 없이 balance 조회하면 400."""
        token = await _register_login(client, "sync4@example.com")
        resp = await client.post(
            "/sync/balance",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_balance_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        """인증 없이 balance 조회하면 401."""
        resp = await client.post("/sync/balance")
        assert resp.status_code in (401, 403)

    async def _setup_linked_portfolio(
        self, client: AsyncClient, email: str
    ) -> tuple[str, int]:
        """Register user, add KIS account, trigger balance sync to create portfolio.

        Returns (token, portfolio_id).
        """
        token = await _register_login(client, email)
        headers = {"Authorization": f"Bearer {token}"}

        await _add_kis_account(client, token)

        summary, holdings = _make_balance_raw_result()
        with patch(
            "app.api.sync._fetch_balance_raw",
            new_callable=AsyncMock,
            return_value=(summary, holdings),
        ):
            await client.post("/sync/balance", headers=headers)

        portfolios_resp = await client.get("/portfolios", headers=headers)
        pid = portfolios_resp.json()[0]["id"]
        return token, pid

    async def test_sync_portfolio_success(self, client: AsyncClient) -> None:
        """KIS 계좌와 연결된 포트폴리오 동기화 성공."""
        token, pid = await self._setup_linked_portfolio(client, "sync5@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        holdings = _mock_kis_holdings()

        with (
            patch(
                "app.api.sync.fetch_account_holdings",
                new_callable=AsyncMock,
                return_value=holdings,
            ),
            patch(
                "app.api.sync.fetch_overseas_account_holdings",
                new_callable=AsyncMock,
                return_value=([], {}),
            ),
        ):
            resp = await client.post(f"/sync/{pid}", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "inserted" in data or "updated" in data or "deleted" in data

    async def test_sync_portfolio_kis_error_returns_502(self, client: AsyncClient) -> None:
        """KIS API 오류 시 502 반환."""
        token, pid = await self._setup_linked_portfolio(client, "sync6@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        with (
            patch(
                "app.api.sync.fetch_account_holdings",
                new_callable=AsyncMock,
                side_effect=RuntimeError("KIS API failure"),
            ),
            patch(
                "app.api.sync.fetch_overseas_account_holdings",
                new_callable=AsyncMock,
                return_value=([], {}),
            ),
        ):
            resp = await client.post(f"/sync/{pid}", headers=headers)

        assert resp.status_code == 502

    async def test_balance_with_kis_account_success(self, client: AsyncClient) -> None:
        """KIS 계좌가 있으면 balance 조회 성공."""
        token = await _register_login(client, "sync7@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        await _add_kis_account(client, token)

        summary, holdings = _make_balance_raw_result()

        with patch(
            "app.api.sync._fetch_balance_raw",
            new_callable=AsyncMock,
            return_value=(summary, holdings),
        ):
            resp = await client.post("/sync/balance", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "accounts" in data
        assert len(data["accounts"]) >= 1
        acct = data["accounts"][0]
        assert "label" in acct
        assert "account_no" in acct

    async def test_balance_error_per_account_returns_partial_result(
        self, client: AsyncClient
    ) -> None:
        """계좌 잔고 조회 실패 시 에러 필드가 포함된 계좌 항목 반환."""
        token = await _register_login(client, "sync8@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        await _add_kis_account(client, token)

        with patch(
            "app.api.sync._fetch_balance_raw",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Simulated failure"),
        ):
            resp = await client.post("/sync/balance", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["accounts"]) == 1
        assert "error" in data["accounts"][0]

    async def test_sync_logs_after_sync(self, client: AsyncClient) -> None:
        """동기화 후 logs 조회 시 항목이 포함됨."""
        token, pid = await self._setup_linked_portfolio(client, "sync9@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        with (
            patch(
                "app.api.sync.fetch_account_holdings",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.sync.fetch_overseas_account_holdings",
                new_callable=AsyncMock,
                return_value=([], {}),
            ),
        ):
            await client.post(f"/sync/{pid}", headers=headers)

        logs_resp = await client.get("/sync/logs", headers=headers)
        assert logs_resp.status_code == 200
        data = logs_resp.json()
        assert "items" in data
        assert "next_cursor" in data
        assert "has_more" in data
        assert len(data["items"]) >= 1
        log = data["items"][0]
        assert "id" in log
        assert "status" in log
        assert "synced_at" in log

    async def test_sync_logs_cursor_pagination(self, client: AsyncClient) -> None:
        """cursor 기반 페이지네이션: cursor 없으면 최신 N건, cursor 있으면 이전 건 반환."""
        token, pid = await self._setup_linked_portfolio(client, "sync10@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Trigger 3 syncs to create 3 log entries
        for _ in range(3):
            with (
                patch(
                    "app.api.sync.fetch_account_holdings",
                    new_callable=AsyncMock,
                    return_value=[],
                ),
                patch(
                    "app.api.sync.fetch_overseas_account_holdings",
                    new_callable=AsyncMock,
                    return_value=([], {}),
                ),
            ):
                await client.post(f"/sync/{pid}", headers=headers)

        # First page: no cursor, limit=2
        resp1 = await client.get(
            "/sync/logs", params={"limit": 2}, headers=headers
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert len(data1["items"]) == 2
        assert data1["has_more"] is True
        assert data1["next_cursor"] is not None

        # Second page: use cursor from first page
        cursor = data1["next_cursor"]
        resp2 = await client.get(
            "/sync/logs", params={"limit": 2, "cursor": cursor}, headers=headers
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        # Should return remaining items (at least 1)
        assert len(data2["items"]) >= 1
        # All items on page 2 should have lower id than cursor
        for item in data2["items"]:
            assert item["id"] < cursor

    async def test_sync_logs_limit_param(self, client: AsyncClient) -> None:
        """limit 파라미터 동작 확인."""
        token = await _register_login(client, "sync10b@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            "/sync/logs",
            params={"limit": 10},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_sync_other_user_portfolio_returns_404(
        self, client: AsyncClient
    ) -> None:
        """다른 사용자의 포트폴리오 동기화 시 404."""
        token1 = await _register_login(client, "sync11a@example.com")
        token2 = await _register_login(client, "sync11b@example.com")

        headers1 = {"Authorization": f"Bearer {token1}"}

        port = await client.post(
            "/portfolios",
            json={"name": "owner portfolio"},
            headers=headers1,
        )
        pid = port.json()["id"]

        resp = await client.post(
            f"/sync/{pid}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 404
