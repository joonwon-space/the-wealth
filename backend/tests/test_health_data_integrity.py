"""GET /health/data-integrity, /health/holdings-reconciliation 엔드포인트 테스트.

app/api/health.py 의 data_integrity_check, holdings_reconciliation 핸들러와
_last_n_weekdays 헬퍼를 검증한다.
"""

from datetime import date

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str) -> str:
    """Register user and return access token."""
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# _last_n_weekdays unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLastNWeekdays:
    def test_returns_n_weekdays(self) -> None:
        """반환된 날짜 리스트의 길이는 n 이어야 한다."""
        from app.api.health import _last_n_weekdays

        result = _last_n_weekdays(7, date(2026, 3, 20))
        assert len(result) == 7

    def test_excludes_weekends(self) -> None:
        """반환된 날짜 중 주말(토=5, 일=6)이 없어야 한다."""
        from app.api.health import _last_n_weekdays

        result = _last_n_weekdays(10, date(2026, 3, 20))
        for d in result:
            assert d.weekday() < 5, f"{d} is a weekend"

    def test_reference_date_included_if_weekday(self) -> None:
        """reference 날짜가 평일이면 결과에 포함되어야 한다."""
        from app.api.health import _last_n_weekdays

        ref = date(2026, 3, 20)  # Friday
        assert ref.weekday() == 4  # Confirm it's a Friday
        result = _last_n_weekdays(1, ref)
        assert result[0] == ref

    def test_reference_weekend_skipped(self) -> None:
        """reference 날짜가 주말이면 건너뛰고 이전 평일을 반환해야 한다."""
        from app.api.health import _last_n_weekdays

        ref = date(2026, 3, 21)  # Saturday
        assert ref.weekday() == 5
        result = _last_n_weekdays(1, ref)
        assert result[0] == date(2026, 3, 20)  # Previous Friday

    def test_dates_in_descending_order_from_reference(self) -> None:
        """날짜는 reference 에서 시작해 과거 방향으로 반환되어야 한다."""
        from app.api.health import _last_n_weekdays

        result = _last_n_weekdays(5, date(2026, 3, 20))
        for i in range(len(result) - 1):
            assert result[i] >= result[i + 1]


# ---------------------------------------------------------------------------
# GET /health/data-integrity
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDataIntegrityCheck:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        """인증 없이 요청하면 401/403 반환."""
        resp = await client.get("/health/data-integrity")
        assert resp.status_code in (401, 403)

    async def test_returns_status_and_fields(self, client: AsyncClient) -> None:
        """응답에 status, checked_weekdays, missing_snapshots, present_snapshots 포함."""
        token = await _register_and_login(client, "di_fields@example.com")
        resp = await client.get("/health/data-integrity", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checked_weekdays" in data
        assert "missing_snapshots" in data
        assert "present_snapshots" in data

    async def test_checked_weekdays_is_seven(self, client: AsyncClient) -> None:
        """checked_weekdays 는 7 이어야 한다."""
        token = await _register_and_login(client, "di_seven@example.com")
        resp = await client.get("/health/data-integrity", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["checked_weekdays"] == 7

    async def test_status_degraded_when_no_snapshots(self, client: AsyncClient) -> None:
        """스냅샷이 없으면 status 는 'degraded' 이어야 한다."""
        token = await _register_and_login(client, "di_degraded@example.com")
        resp = await client.get("/health/data-integrity", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        # No price snapshots in test DB, so all weekdays are missing
        assert data["status"] == "degraded"
        assert len(data["missing_snapshots"]) > 0

    async def test_missing_and_present_are_lists(self, client: AsyncClient) -> None:
        """missing_snapshots, present_snapshots 는 리스트여야 한다."""
        token = await _register_and_login(client, "di_lists@example.com")
        resp = await client.get("/health/data-integrity", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["missing_snapshots"], list)
        assert isinstance(data["present_snapshots"], list)

    async def test_total_equals_checked_weekdays(self, client: AsyncClient) -> None:
        """missing + present 의 합이 checked_weekdays 와 같아야 한다."""
        token = await _register_and_login(client, "di_total@example.com")
        resp = await client.get("/health/data-integrity", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        total = len(data["missing_snapshots"]) + len(data["present_snapshots"])
        assert total == data["checked_weekdays"]

    async def test_dates_are_iso_format(self, client: AsyncClient) -> None:
        """날짜 문자열은 ISO 8601 형식(YYYY-MM-DD)이어야 한다."""
        token = await _register_and_login(client, "di_iso@example.com")
        resp = await client.get("/health/data-integrity", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        for date_str in data["missing_snapshots"] + data["present_snapshots"]:
            # Verify parseable as date
            parsed = date.fromisoformat(date_str)
            assert parsed is not None


# ---------------------------------------------------------------------------
# GET /health/holdings-reconciliation
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestHoldingsReconciliation:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        """인증 없이 요청하면 401/403 반환."""
        resp = await client.get("/health/holdings-reconciliation")
        assert resp.status_code in (401, 403)

    async def test_returns_status_and_fields(self, client: AsyncClient) -> None:
        """응답에 status, checked_holdings, mismatches 포함."""
        token = await _register_and_login(client, "rec_fields@example.com")
        resp = await client.get("/health/holdings-reconciliation", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checked_holdings" in data
        assert "mismatches" in data

    async def test_no_portfolio_returns_ok(self, client: AsyncClient) -> None:
        """포트폴리오 없는 사용자는 status=ok, checked=0, mismatches=[]."""
        token = await _register_and_login(client, "rec_empty@example.com")
        resp = await client.get("/health/holdings-reconciliation", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["checked_holdings"] == 0
        assert data["mismatches"] == []

    async def test_ok_when_holding_matches_transaction(self, client: AsyncClient) -> None:
        """BUY 거래와 보유 수량이 일치하면 status=ok, mismatches=[]."""
        token = await _register_and_login(client, "rec_match@example.com")
        auth = _auth(token)

        # Create portfolio
        port_resp = await client.post(
            "/portfolios",
            json={"name": "테스트 포트폴리오"},
            headers=auth,
        )
        assert port_resp.status_code == 201
        pid = port_resp.json()["id"]

        # Add holding
        await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": "10",
                "avg_price": "70000",
            },
            headers=auth,
        )

        # Add BUY transaction matching quantity
        await client.post(
            f"/portfolios/{pid}/transactions",
            json={
                "ticker": "005930",
                "type": "BUY",
                "quantity": "10",
                "price": "70000",
                "traded_at": "2026-01-01T09:00:00",
            },
            headers=auth,
        )

        resp = await client.get("/health/holdings-reconciliation", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["mismatches"] == []

    async def test_checked_holdings_count(self, client: AsyncClient) -> None:
        """checked_holdings 는 실제 보유 종목 수와 일치해야 한다."""
        token = await _register_and_login(client, "rec_count@example.com")
        auth = _auth(token)

        port_resp = await client.post(
            "/portfolios",
            json={"name": "테스트"},
            headers=auth,
        )
        pid = port_resp.json()["id"]

        for ticker, name in [("005930", "삼성전자"), ("000660", "SK하이닉스")]:
            await client.post(
                f"/portfolios/{pid}/holdings",
                json={
                    "ticker": ticker,
                    "name": name,
                    "quantity": "5",
                    "avg_price": "100000",
                },
                headers=auth,
            )

        resp = await client.get("/health/holdings-reconciliation", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert data["checked_holdings"] == 2

    async def test_degraded_when_mismatch_detected(self, client: AsyncClient) -> None:
        """거래 수량이 보유 수량과 다르면 status=degraded, mismatches 에 항목 포함."""
        token = await _register_and_login(client, "rec_mismatch@example.com")
        auth = _auth(token)

        port_resp = await client.post(
            "/portfolios",
            json={"name": "불일치 포트폴리오"},
            headers=auth,
        )
        pid = port_resp.json()["id"]

        # holding quantity = 10
        await client.post(
            f"/portfolios/{pid}/holdings",
            json={
                "ticker": "005930",
                "name": "삼성전자",
                "quantity": "10",
                "avg_price": "70000",
            },
            headers=auth,
        )

        # transaction BUY quantity = 8 (mismatch)
        await client.post(
            f"/portfolios/{pid}/transactions",
            json={
                "ticker": "005930",
                "type": "BUY",
                "quantity": "8",
                "price": "70000",
                "traded_at": "2026-01-01T09:00:00",
            },
            headers=auth,
        )

        resp = await client.get("/health/holdings-reconciliation", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert len(data["mismatches"]) == 1
        mismatch = data["mismatches"][0]
        assert mismatch["ticker"] == "005930"
        assert "holdings_quantity" in mismatch
        assert "transaction_net_quantity" in mismatch
        assert "diff" in mismatch
