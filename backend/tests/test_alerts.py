"""Unit and integration tests for the alerts API and check_triggered_alerts."""

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.api.alerts import check_triggered_alerts


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
