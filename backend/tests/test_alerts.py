"""Unit and integration tests for the alerts API and check_triggered_alerts."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.api.alerts import check_and_dedup_alerts, check_triggered_alerts, _is_cooldown_active


# ---------------------------------------------------------------------------
# Unit tests for check_triggered_alerts (pure function, no DB/HTTP needed)
# ---------------------------------------------------------------------------


def _mock_alert(
    id: int,
    ticker: str,
    condition: str,
    threshold: float,
    is_active: bool = True,
    name: str = "",
) -> Any:
    a = MagicMock()
    a.id = id
    a.ticker = ticker
    a.condition = condition
    a.threshold = threshold
    a.is_active = is_active
    a.name = name
    return a


@pytest.mark.unit
class TestCheckTriggeredAlerts:
    def test_empty_alerts_returns_empty(self) -> None:
        result = check_triggered_alerts([], {"005930": Decimal("75000")})
        assert result == []

    def test_empty_prices_returns_empty(self) -> None:
        alert = _mock_alert(1, "005930", "above", 70000)
        result = check_triggered_alerts([alert], {})
        assert result == []

    def test_inactive_alert_not_triggered(self) -> None:
        alert = _mock_alert(1, "005930", "above", 70000, is_active=False)
        result = check_triggered_alerts([alert], {"005930": Decimal("75000")})
        assert result == []

    def test_above_condition_triggers_when_price_equals_threshold(self) -> None:
        alert = _mock_alert(1, "005930", "above", 75000)
        result = check_triggered_alerts([alert], {"005930": Decimal("75000")})
        assert len(result) == 1
        assert result[0]["ticker"] == "005930"

    def test_above_condition_triggers_when_price_exceeds_threshold(self) -> None:
        alert = _mock_alert(1, "005930", "above", 70000)
        result = check_triggered_alerts([alert], {"005930": Decimal("80000")})
        assert len(result) == 1

    def test_above_condition_not_triggered_when_price_below_threshold(self) -> None:
        alert = _mock_alert(1, "005930", "above", 80000)
        result = check_triggered_alerts([alert], {"005930": Decimal("75000")})
        assert result == []

    def test_below_condition_triggers_when_price_equals_threshold(self) -> None:
        alert = _mock_alert(1, "005930", "below", 75000)
        result = check_triggered_alerts([alert], {"005930": Decimal("75000")})
        assert len(result) == 1

    def test_below_condition_triggers_when_price_under_threshold(self) -> None:
        alert = _mock_alert(1, "005930", "below", 80000)
        result = check_triggered_alerts([alert], {"005930": Decimal("70000")})
        assert len(result) == 1

    def test_below_condition_not_triggered_when_price_above_threshold(self) -> None:
        alert = _mock_alert(1, "005930", "below", 70000)
        result = check_triggered_alerts([alert], {"005930": Decimal("75000")})
        assert result == []

    def test_ticker_mismatch_not_triggered(self) -> None:
        alert = _mock_alert(1, "005930", "above", 70000)
        result = check_triggered_alerts([alert], {"000660": Decimal("120000")})
        assert result == []

    def test_multiple_alerts_multiple_triggers(self) -> None:
        alerts = [
            _mock_alert(1, "005930", "above", 70000),
            _mock_alert(2, "000660", "below", 130000),
            _mock_alert(3, "035420", "above", 300000),  # not triggered
        ]
        prices = {
            "005930": Decimal("75000"),
            "000660": Decimal("120000"),
            "035420": Decimal("200000"),
        }
        result = check_triggered_alerts(alerts, prices)
        assert len(result) == 2
        tickers = {r["ticker"] for r in result}
        assert tickers == {"005930", "000660"}

    def test_triggered_result_contains_expected_fields(self) -> None:
        alert = _mock_alert(42, "005930", "above", 70000, name="삼성전자")
        result = check_triggered_alerts([alert], {"005930": Decimal("75000")})
        assert len(result) == 1
        r = result[0]
        assert r["id"] == 42
        assert r["ticker"] == "005930"
        assert r["name"] == "삼성전자"
        assert r["condition"] == "above"
        assert r["threshold"] == 70000.0
        assert r["current_price"] == 75000.0

    def test_none_price_not_triggered(self) -> None:
        alert = _mock_alert(1, "005930", "above", 70000)
        result = check_triggered_alerts([alert], {"005930": None})
        assert result == []


# ---------------------------------------------------------------------------
# Integration tests for /alerts API endpoints
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


@pytest.mark.integration
class TestAlertsAPI:
    async def test_list_alerts_empty(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "alerts1@test.com")
        resp = await client.get("/alerts", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_alert(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "alerts2@test.com")
        resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "name": "삼성전자", "condition": "above", "threshold": 80000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["condition"] == "above"
        assert float(data["threshold"]) == 80000.0
        assert data["is_active"] is True

    async def test_list_after_create(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "alerts3@test.com")
        await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": 80000},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get("/alerts", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_delete_alert(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "alerts4@test.com")
        create_resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": 80000},
            headers={"Authorization": f"Bearer {token}"},
        )
        alert_id = create_resp.json()["id"]
        del_resp = await client.delete(
            f"/alerts/{alert_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert del_resp.status_code == 204
        list_resp = await client.get("/alerts", headers={"Authorization": f"Bearer {token}"})
        assert list_resp.json() == []

    async def test_delete_other_users_alert_returns_404(self, client: AsyncClient) -> None:
        token1 = await _register_and_login(client, "alerts5@test.com")
        token2 = await _register_and_login(client, "alerts6@test.com")
        create_resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": 80000},
            headers={"Authorization": f"Bearer {token1}"},
        )
        alert_id = create_resp.json()["id"]
        # User 2 tries to delete user 1's alert
        del_resp = await client.delete(
            f"/alerts/{alert_id}", headers={"Authorization": f"Bearer {token2}"}
        )
        assert del_resp.status_code == 404

    async def test_create_alert_invalid_threshold(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "alerts7@test.com")
        resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": -100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_create_alert_invalid_condition(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "alerts8@test.com")
        resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "invalid", "threshold": 80000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_create_alert_empty_ticker_returns_422(
        self, client: AsyncClient
    ) -> None:
        """빈 ticker는 422 반환."""
        token = await _register_and_login(client, "alerts_emptyticker@test.com")
        resp = await client.post(
            "/alerts",
            json={"ticker": "   ", "condition": "above", "threshold": 80000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_patch_alert_deactivate(self, client: AsyncClient) -> None:
        """PATCH로 알림 비활성화."""
        token = await _register_and_login(client, "alerts_patch1@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": 80000},
            headers=headers,
        )
        alert_id = create_resp.json()["id"]

        patch_resp = await client.patch(
            f"/alerts/{alert_id}",
            json={"is_active": False},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["is_active"] is False

    async def test_patch_alert_activate(self, client: AsyncClient) -> None:
        """PATCH로 알림 재활성화."""
        token = await _register_and_login(client, "alerts_patch2@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": 80000},
            headers=headers,
        )
        alert_id = create_resp.json()["id"]
        # 먼저 비활성화
        await client.patch(f"/alerts/{alert_id}", json={"is_active": False}, headers=headers)
        # 재활성화
        patch_resp = await client.patch(
            f"/alerts/{alert_id}",
            json={"is_active": True},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["is_active"] is True

    async def test_patch_alert_change_threshold(self, client: AsyncClient) -> None:
        """PATCH로 임계값 변경."""
        token = await _register_and_login(client, "alerts_patch3@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": 80000},
            headers=headers,
        )
        alert_id = create_resp.json()["id"]
        patch_resp = await client.patch(
            f"/alerts/{alert_id}",
            json={"threshold": 90000},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert float(patch_resp.json()["threshold"]) == 90000.0

    async def test_patch_alert_not_found_returns_404(self, client: AsyncClient) -> None:
        """존재하지 않는 알림 PATCH 시 404 반환."""
        token = await _register_and_login(client, "alerts_patch4@test.com")
        resp = await client.patch(
            "/alerts/99999",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_patch_alert_invalid_threshold_returns_422(
        self, client: AsyncClient
    ) -> None:
        """PATCH로 0 이하 임계값 설정 시 422 반환."""
        token = await _register_and_login(client, "alerts_patch5@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = await client.post(
            "/alerts",
            json={"ticker": "005930", "condition": "above", "threshold": 80000},
            headers=headers,
        )
        alert_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/alerts/{alert_id}",
            json={"threshold": -1},
            headers=headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Unit tests for _is_cooldown_active and check_and_dedup_alerts
# ---------------------------------------------------------------------------


def _mock_dedup_alert(
    id: int,
    ticker: str,
    condition: str,
    threshold: float,
    is_active: bool = True,
    last_triggered_at: datetime | None = None,
    name: str = "",
) -> Any:
    a = MagicMock()
    a.id = id
    a.ticker = ticker
    a.condition = condition
    a.threshold = threshold
    a.is_active = is_active
    a.last_triggered_at = last_triggered_at
    a.name = name
    return a


@pytest.mark.unit
class TestIsCooldownActive:
    def test_no_last_triggered_not_cooldown(self) -> None:
        """last_triggered_at 없으면 쿨다운 아님."""
        alert = _mock_dedup_alert(1, "005930", "above", 70000, last_triggered_at=None)
        now = datetime.now(timezone.utc)
        assert _is_cooldown_active(alert, now) is False

    def test_just_triggered_is_cooldown(self) -> None:
        """방금 트리거됐으면 쿨다운 중."""
        now = datetime.now(timezone.utc)
        alert = _mock_dedup_alert(
            1, "005930", "above", 70000, last_triggered_at=now - timedelta(seconds=10)
        )
        assert _is_cooldown_active(alert, now) is True

    def test_expired_cooldown_not_active(self) -> None:
        """1시간 초과 시 쿨다운 해제."""
        now = datetime.now(timezone.utc)
        alert = _mock_dedup_alert(
            1, "005930", "above", 70000,
            last_triggered_at=now - timedelta(hours=2)
        )
        assert _is_cooldown_active(alert, now) is False

    def test_naive_datetime_treated_as_utc(self) -> None:
        """tzinfo 없는 last_triggered_at을 UTC로 처리."""
        now = datetime.now(timezone.utc)
        naive_ts = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10)
        alert = _mock_dedup_alert(
            1, "005930", "above", 70000, last_triggered_at=naive_ts
        )
        # 10초 전 트리거는 쿨다운 중이어야 함
        assert _is_cooldown_active(alert, now) is True


@pytest.mark.unit
class TestCheckAndDedupAlerts:
    def test_empty_returns_empty(self) -> None:
        result = check_and_dedup_alerts([], {"005930": Decimal("75000")})
        assert result == []

    def test_inactive_alert_skipped(self) -> None:
        alert = _mock_dedup_alert(1, "005930", "above", 70000, is_active=False)
        result = check_and_dedup_alerts([alert], {"005930": Decimal("75000")})
        assert result == []

    def test_cooldown_alert_skipped(self) -> None:
        """쿨다운 중인 알림은 다시 트리거되지 않음."""
        now = datetime.now(timezone.utc)
        alert = _mock_dedup_alert(
            1, "005930", "above", 70000,
            last_triggered_at=now - timedelta(seconds=30),
        )
        result = check_and_dedup_alerts([alert], {"005930": Decimal("75000")})
        assert result == []

    def test_triggered_alert_deactivated_and_marked(self) -> None:
        """트리거된 알림은 is_active=False, last_triggered_at 설정."""
        alert = _mock_dedup_alert(1, "005930", "above", 70000)
        result = check_and_dedup_alerts([alert], {"005930": Decimal("80000")})
        assert len(result) == 1
        assert alert.is_active is False
        assert alert.last_triggered_at is not None

    def test_not_hit_returns_empty(self) -> None:
        """조건 미충족 시 빈 결과."""
        alert = _mock_dedup_alert(1, "005930", "above", 90000)
        result = check_and_dedup_alerts([alert], {"005930": Decimal("80000")})
        assert result == []

    def test_none_price_skipped(self) -> None:
        alert = _mock_dedup_alert(1, "005930", "above", 70000)
        result = check_and_dedup_alerts([alert], {"005930": None})
        assert result == []

    def test_below_condition_triggers(self) -> None:
        alert = _mock_dedup_alert(2, "000660", "below", 150000)
        result = check_and_dedup_alerts([alert], {"000660": Decimal("140000")})
        assert len(result) == 1
        assert result[0]["ticker"] == "000660"
