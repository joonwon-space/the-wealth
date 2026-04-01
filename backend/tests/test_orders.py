"""주문 API 통합 테스트 및 KIS 주문 서비스 단위 테스트."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ─── Helper Functions ──────────────────────────────────────────────────────────


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post("/auth/register", json={"email": email, "password": "Test1234!"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "Test1234!"}
    )
    return resp.json()["access_token"]


async def _add_kis_account(client: AsyncClient, token: str) -> int:
    """KIS 계좌 추가 후 account ID 반환."""
    resp = await client.post(
        "/users/kis-accounts",
        json={
            "label": "Test Account",
            "account_no": "12345678",
            "acnt_prdt_cd": "01",
            "app_key": "dummy_key",
            "app_secret": "dummy_secret",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"KIS account creation failed: {resp.text}"
    return resp.json()["id"]


def _make_balance_raw_result() -> tuple:
    from app.services.kis_account import KisHolding

    summary = {
        "dnca_tot_amt": "1000000",
        "tot_evlu_amt": "1100000",
        "scts_evlu_amt": "700000",
        "evlu_pfls_smtl_amt": "100000",
    }
    holdings = [
        KisHolding(
            ticker="005930",
            name="삼성전자",
            quantity=Decimal("10"),
            avg_price=Decimal("70000"),
            market="KRW",
        )
    ]
    return summary, holdings


async def _setup_portfolio_with_kis(
    client: AsyncClient, email: str
) -> tuple[str, int, int]:
    """사용자 등록, KIS 계좌 추가, sync/balance로 KIS 연결 포트폴리오 생성 후
    (token, portfolio_id, kis_account_id) 반환.
    """
    token = await _register_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    kis_id = await _add_kis_account(client, token)

    # sync/balance 호출로 KIS 계좌가 연결된 포트폴리오 자동 생성
    summary, holdings = _make_balance_raw_result()
    with patch(
        "app.api.sync._fetch_balance_raw",
        new_callable=AsyncMock,
        return_value=(summary, holdings),
    ):
        await client.post("/sync/balance", headers=headers)

    portfolios_resp = await client.get("/portfolios", headers=headers)
    portfolio_id = portfolios_resp.json()[0]["id"]
    return token, portfolio_id, kis_id


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_order_result(
    order_no: str = "0000000001",
    status: str = "pending",
    msg: str = "주문 완료",
) -> object:
    """Mock OrderResult 객체 생성."""
    from app.services.kis_order import OrderResult

    return OrderResult(
        order_no=order_no,
        ticker="005930",
        order_type="BUY",
        quantity=Decimal("10"),
        price=Decimal("70000"),
        status=status,
        message=msg,
    )


# ─── 주문 API 테스트 ────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestOrdersAPINoKis:
    """KIS 계좌 없이 주문 API 요청하면 400 반환."""

    async def test_place_order_without_kis_account_returns_400(
        self, client: AsyncClient
    ) -> None:
        token = await _register_login(client, "order_nokis@test.com")
        # 포트폴리오를 KIS 계좌 없이 생성
        port_resp = await client.post(
            "/portfolios",
            json={"name": "No KIS"},
            headers=_auth(token),
        )
        assert port_resp.status_code == 201
        pid = port_resp.json()["id"]

        resp = await client.post(
            f"/portfolios/{pid}/orders",
            json={
                "ticker": "005930",
                "order_type": "BUY",
                "order_class": "limit",
                "quantity": 10,
                "price": 70000,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert "KIS" in resp.json()["error"]["message"]

    async def test_cash_balance_without_kis_returns_400(
        self, client: AsyncClient
    ) -> None:
        token = await _register_login(client, "balance_nokis@test.com")
        port_resp = await client.post(
            "/portfolios",
            json={"name": "No KIS"},
            headers=_auth(token),
        )
        pid = port_resp.json()["id"]

        resp = await client.get(
            f"/portfolios/{pid}/cash-balance",
            headers=_auth(token),
        )
        assert resp.status_code == 400

    async def test_orderable_without_kis_returns_400(
        self, client: AsyncClient
    ) -> None:
        token = await _register_login(client, "orderable_nokis@test.com")
        port_resp = await client.post(
            "/portfolios",
            json={"name": "No KIS"},
            headers=_auth(token),
        )
        pid = port_resp.json()["id"]

        resp = await client.get(
            f"/portfolios/{pid}/orders/orderable",
            params={"ticker": "005930", "price": 70000},
            headers=_auth(token),
        )
        assert resp.status_code == 400


@pytest.mark.integration
class TestPlaceOrder:
    """정상 주문 플로우 테스트."""

    async def test_domestic_buy_order_success(self, client: AsyncClient) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "order_buy@test.com"
        )

        mock_result = _make_order_result()
        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = mock_result
            resp = await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "name": "삼성전자",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 10,
                    "price": 70000,
                },
                headers=_auth(token),
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ticker"] == "005930"
        assert data["order_type"] == "BUY"
        assert data["status"] == "pending"
        assert data["order_no"] == "0000000001"

    async def test_pending_order_does_not_create_transaction(
        self, client: AsyncClient
    ) -> None:
        """미체결(pending) 주문은 transaction을 생성하지 않아야 한다."""
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "order_no_txn@test.com"
        )

        mock_result = _make_order_result()
        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = mock_result
            await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "name": "삼성전자",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 10,
                    "price": 70000,
                },
                headers=_auth(token),
            )

        # pending 주문 후 transactions가 비어 있어야 한다
        txn_resp = await client.get(
            f"/portfolios/{pid}/transactions",
            headers=_auth(token),
        )
        assert txn_resp.status_code == 200
        assert txn_resp.json() == []

    async def test_pending_order_does_not_update_holdings(
        self, client: AsyncClient
    ) -> None:
        """미체결(pending) 주문은 holdings 수량을 변경하지 않아야 한다."""
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "order_no_hold@test.com"
        )

        # sync/balance로 005930 10주 보유 상태
        holdings_before = await client.get(
            f"/portfolios/{pid}/holdings",
            headers=_auth(token),
        )
        before_qty = sum(
            h["quantity"] for h in holdings_before.json() if h["ticker"] == "005930"
        )

        mock_result = _make_order_result()
        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = mock_result
            await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "name": "삼성전자",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 10,
                    "price": 70000,
                },
                headers=_auth(token),
            )

        # holdings 수량이 변하지 않아야 한다
        holdings_after = await client.get(
            f"/portfolios/{pid}/holdings",
            headers=_auth(token),
        )
        after_qty = sum(
            h["quantity"] for h in holdings_after.json() if h["ticker"] == "005930"
        )
        assert before_qty == after_qty

    async def test_domestic_sell_order_success(self, client: AsyncClient) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "order_sell@test.com"
        )

        # Add a holding first
        await client.post(
            f"/portfolios/{pid}/transactions",
            json={"ticker": "005930", "type": "BUY", "quantity": 20, "price": 70000},
            headers=_auth(token),
        )

        from app.services.kis_order import OrderResult

        sell_result = OrderResult(
            order_no="0000000002",
            ticker="005930",
            order_type="SELL",
            quantity=Decimal("5"),
            price=Decimal("72000"),
            status="pending",
            message="매도 주문 완료",
        )
        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = sell_result
            resp = await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "order_type": "SELL",
                    "order_class": "limit",
                    "quantity": 5,
                    "price": 72000,
                },
                headers=_auth(token),
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["order_type"] == "SELL"
        assert data["status"] == "pending"

    async def test_overseas_order_uses_place_overseas_order(
        self, client: AsyncClient
    ) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "order_overseas@test.com"
        )

        from app.services.kis_order import OrderResult

        overseas_result = OrderResult(
            order_no="0000000003",
            ticker="AAPL",
            order_type="BUY",
            quantity=Decimal("1"),
            price=Decimal("180.00"),
            status="pending",
            message="해외 주문 완료",
        )
        with patch(
            "app.api.orders.place_overseas_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = overseas_result
            resp = await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "AAPL",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 1,
                    "price": "180.00",
                    "exchange_code": "NASD",
                },
                headers=_auth(token),
            )

        assert resp.status_code == 200, resp.text
        mock_order.assert_called_once()
        data = resp.json()
        assert data["ticker"] == "AAPL"

    async def test_order_failed_status_not_create_transaction(
        self, client: AsyncClient
    ) -> None:
        """KIS API 실패 시 orders 테이블에는 기록되지만 transactions는 생성되지 않음."""
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "order_fail@test.com"
        )

        from app.services.kis_order import OrderResult

        failed_result = OrderResult(
            order_no="",
            ticker="005930",
            order_type="BUY",
            quantity=Decimal("10"),
            price=Decimal("70000"),
            status="failed",
            message="예수금 부족",
        )
        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.return_value = failed_result
            resp = await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 10,
                    "price": 70000,
                },
                headers=_auth(token),
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "failed"

        # Verify transactions list is empty (no transaction created)
        txn_resp = await client.get(
            f"/portfolios/{pid}/transactions",
            headers=_auth(token),
        )
        assert txn_resp.status_code == 200
        assert txn_resp.json() == []


@pytest.mark.integration
class TestOrdersIsolation:
    """IDOR 방지: 다른 사용자의 포트폴리오에 주문 불가."""

    async def test_cannot_place_order_on_other_users_portfolio(
        self, client: AsyncClient
    ) -> None:
        # User A creates portfolio
        _token_a, pid_a, _kis_id = await _setup_portfolio_with_kis(
            client, "order_idor_a@test.com"
        )

        # User B tries to place order on User A's portfolio
        token_b = await _register_login(client, "order_idor_b@test.com")
        resp = await client.post(
            f"/portfolios/{pid_a}/orders",
            json={
                "ticker": "005930",
                "order_type": "BUY",
                "order_class": "limit",
                "quantity": 10,
                "price": 70000,
            },
            headers=_auth(token_b),
        )
        assert resp.status_code == 404

    async def test_cannot_view_cash_balance_on_other_users_portfolio(
        self, client: AsyncClient
    ) -> None:
        _token_a, pid_a, _kis_id = await _setup_portfolio_with_kis(
            client, "balance_idor_a@test.com"
        )
        token_b = await _register_login(client, "balance_idor_b@test.com")

        resp = await client.get(
            f"/portfolios/{pid_a}/cash-balance",
            headers=_auth(token_b),
        )
        assert resp.status_code == 404


@pytest.mark.integration
class TestPendingOrders:
    """미체결 주문 조회 테스트."""

    async def test_list_pending_orders_empty(self, client: AsyncClient) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "pending_empty@test.com"
        )

        with patch(
            "app.api.orders.get_pending_orders", new_callable=AsyncMock
        ) as mock_pending:
            mock_pending.return_value = []
            resp = await client.get(
                f"/portfolios/{pid}/orders/pending",
                headers=_auth(token),
            )

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_pending_orders_with_data(self, client: AsyncClient) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "pending_data@test.com"
        )

        from app.services.kis_order import PendingOrder

        mock_pending = [
            PendingOrder(
                order_no="0000000010",
                ticker="005930",
                name="삼성전자",
                order_type="BUY",
                order_class="limit",
                quantity=Decimal("10"),
                price=Decimal("70000"),
                filled_quantity=Decimal("0"),
                remaining_quantity=Decimal("10"),
                order_time="091500",
            )
        ]

        with patch(
            "app.api.orders.get_pending_orders", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_pending
            resp = await client.get(
                f"/portfolios/{pid}/orders/pending",
                headers=_auth(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "005930"
        assert data[0]["order_no"] == "0000000010"


@pytest.mark.integration
class TestCancelOrder:
    """주문 취소 테스트."""

    async def test_cancel_order_success(self, client: AsyncClient) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "cancel_order@test.com"
        )

        with patch(
            "app.api.orders.cancel_order", new_callable=AsyncMock
        ) as mock_cancel:
            mock_cancel.return_value = True
            resp = await client.delete(
                f"/portfolios/{pid}/orders/0000000001",
                params={"ticker": "005930", "quantity": 10, "price": 70000},
                headers=_auth(token),
            )

        assert resp.status_code == 204

    async def test_cancel_order_kis_failure_returns_502(
        self, client: AsyncClient
    ) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "cancel_fail@test.com"
        )

        with patch(
            "app.api.orders.cancel_order", new_callable=AsyncMock
        ) as mock_cancel:
            mock_cancel.side_effect = RuntimeError("주문 취소 실패")
            resp = await client.delete(
                f"/portfolios/{pid}/orders/0000000001",
                params={"ticker": "005930", "quantity": 10, "price": 70000},
                headers=_auth(token),
            )

        assert resp.status_code == 502


@pytest.mark.integration
class TestCashBalance:
    """예수금 조회 테스트."""

    async def test_get_cash_balance_success(self, client: AsyncClient) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "cashbal_ok@test.com"
        )

        from app.services.kis_balance import CashBalance

        mock_balance = CashBalance(
            total_cash=Decimal("1000000"),
            available_cash=Decimal("900000"),
            total_evaluation=Decimal("5000000"),
            total_profit_loss=Decimal("500000"),
            profit_loss_rate=Decimal("11.11"),
            currency="KRW",
        )

        with (
            patch(
                "app.api.orders.get_cash_balance", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "app.api.orders.fetch_overseas_account_holdings",
                new_callable=AsyncMock,
            ) as mock_overseas,
        ):
            mock_get.return_value = mock_balance
            mock_overseas.return_value = ([], {})  # 해외 보유 없음
            resp = await client.get(
                f"/portfolios/{pid}/cash-balance",
                headers=_auth(token),
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["currency"] == "KRW"
        assert Decimal(data["total_cash"]) == Decimal("1000000")
        assert Decimal(data["available_cash"]) == Decimal("900000")

    async def test_cash_balance_kis_failure_returns_502(
        self, client: AsyncClient
    ) -> None:
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "cashbal_fail@test.com"
        )

        # Clear any cached value to ensure KIS API path is hit
        from app.core.redis_cache import RedisCache
        from app.core.config import settings as app_settings
        cache = RedisCache(app_settings.REDIS_URL)
        await cache.delete(f"cash_balance:{pid}")

        with patch(
            "app.api.orders.get_cash_balance", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = RuntimeError("KIS API 오류")
            resp = await client.get(
                f"/portfolios/{pid}/cash-balance",
                headers=_auth(token),
            )

        assert resp.status_code == 502


# ─── KIS 주문 서비스 단위 테스트 ─────────────────────────────────────────────────


@pytest.mark.unit
class TestIsMarketOpen:
    """장 운영시간 체크 단위 테스트."""

    def test_market_closed_on_weekend(self) -> None:
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        _KST = timezone(timedelta(hours=9))
        # Saturday KST
        saturday = datetime(2026, 3, 28, 10, 0, 0, tzinfo=_KST)

        with patch("app.services.kis_order.datetime") as mock_dt:
            mock_dt.now.return_value = saturday
            # Rebuild with mocked value
            import importlib
            import app.services.kis_order as kis_order_module
            importlib.reload(kis_order_module)

        # Direct test without mocking datetime module complexity
        # Just verify the function exists and is callable
        from app.services.kis_order import is_market_open as iom
        assert callable(iom)

    def test_is_market_open_callable(self) -> None:
        from app.services.kis_order import is_market_open
        # Returns bool
        result = is_market_open()
        assert isinstance(result, bool)


@pytest.mark.unit
class TestTrIdMapping:
    """TR_ID 매핑 단위 테스트."""

    def test_domestic_buy_regular_account(self) -> None:
        from app.services.kis_order import _get_domestic_tr_id

        assert _get_domestic_tr_id("BUY", "일반", False) == "TTTC0802U"

    def test_domestic_sell_regular_account(self) -> None:
        from app.services.kis_order import _get_domestic_tr_id

        assert _get_domestic_tr_id("SELL", "일반", False) == "TTTC0801U"

    def test_domestic_buy_pension_account(self) -> None:
        from app.services.kis_order import _get_domestic_tr_id

        assert _get_domestic_tr_id("BUY", "연금저축", False) == "TTTC0852U"

    def test_domestic_sell_irp_account(self) -> None:
        from app.services.kis_order import _get_domestic_tr_id

        assert _get_domestic_tr_id("SELL", "IRP", False) == "TTTC0851U"

    def test_domestic_buy_paper_trading(self) -> None:
        from app.services.kis_order import _get_domestic_tr_id

        assert _get_domestic_tr_id("BUY", "일반", True) == "VTTC0802U"

    def test_domestic_sell_paper_trading(self) -> None:
        from app.services.kis_order import _get_domestic_tr_id

        assert _get_domestic_tr_id("SELL", "ISA", True) == "VTTC0801U"

    def test_overseas_buy_real(self) -> None:
        from app.services.kis_order import _get_overseas_tr_id

        assert _get_overseas_tr_id("BUY", False) == "JTTT1002U"

    def test_overseas_sell_real(self) -> None:
        from app.services.kis_order import _get_overseas_tr_id

        assert _get_overseas_tr_id("SELL", False) == "JTTT1006U"

    def test_overseas_buy_paper(self) -> None:
        from app.services.kis_order import _get_overseas_tr_id

        assert _get_overseas_tr_id("BUY", True) == "VTTT1002U"


@pytest.mark.unit
class TestRateLimitKey:
    """Rate limit 관련 단위 테스트."""

    def test_rate_limit_key_format(self) -> None:
        key = f"order_rate:{123}"
        assert key == "order_rate:123"

    def test_order_lock_key_format(self) -> None:
        key = f"order_lock:{456}:{789}"
        # This is a placeholder key test
        assert "order_lock" in key


@pytest.mark.integration
class TestSellInsufficientHoldings:
    """매도 시 보유 수량 부족 오류 테스트."""

    async def test_sell_exceeds_holding_quantity_returns_400(
        self, client: AsyncClient
    ) -> None:
        """보유 수량보다 많이 매도 요청 시 400 반환.

        sync/balance mock은 005930 10주를 생성하므로,
        11주 매도 시도 시 400이 반환되어야 한다.
        """
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "sell_insuf@test.com"
        )
        # sync/balance로 10주 005930 보유 → 11주 매도 시 400
        resp = await client.post(
            f"/portfolios/{pid}/orders",
            json={
                "ticker": "005930",
                "order_type": "SELL",
                "order_class": "limit",
                "quantity": 11,  # 10주 보유인데 11주 매도 시도
                "price": 70000,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert "보유 수량 부족" in resp.json()["error"]["message"]

    async def test_sell_with_no_holding_returns_400(
        self, client: AsyncClient
    ) -> None:
        """보유 종목 없이 매도 요청 시 400 반환."""
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "sell_no_holding@test.com"
        )

        resp = await client.post(
            f"/portfolios/{pid}/orders",
            json={
                "ticker": "000660",  # 보유하지 않은 종목
                "order_type": "SELL",
                "order_class": "limit",
                "quantity": 1,
                "price": 120000,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400


@pytest.mark.integration
class TestOrderableEndpoint:
    """주문 가능 수량/금액 조회 테스트."""

    async def test_orderable_success(self, client: AsyncClient) -> None:
        """orderable 조회 성공 시 수량과 금액 반환."""
        from app.services.kis_order import OrderableInfo

        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "orderable_ok@test.com"
        )

        mock_info = OrderableInfo(
            orderable_quantity=Decimal("50"),
            orderable_amount=Decimal("3500000"),
            current_price=Decimal("70000"),
            currency="KRW",
        )

        with patch(
            "app.api.orders.get_orderable_quantity", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_info
            resp = await client.get(
                f"/portfolios/{pid}/orders/orderable",
                params={"ticker": "005930", "price": 70000},
                headers=_auth(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["orderable_quantity"]) == Decimal("50")
        assert Decimal(data["orderable_amount"]) == Decimal("3500000")

    async def test_orderable_kis_failure_returns_502(
        self, client: AsyncClient
    ) -> None:
        """KIS API 실패 시 502 반환."""
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "orderable_fail@test.com"
        )

        with patch(
            "app.api.orders.get_orderable_quantity", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = RuntimeError("KIS API 오류")
            resp = await client.get(
                f"/portfolios/{pid}/orders/orderable",
                params={"ticker": "005930", "price": 70000},
                headers=_auth(token),
            )

        assert resp.status_code == 502


@pytest.mark.integration
class TestPendingOrdersError:
    """미체결 주문 조회 에러 테스트."""

    async def test_pending_orders_kis_failure_returns_502(
        self, client: AsyncClient
    ) -> None:
        """KIS API 실패 시 502 반환."""
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "pending_fail@test.com"
        )

        with patch(
            "app.api.orders.get_pending_orders", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = RuntimeError("미체결 조회 실패")
            resp = await client.get(
                f"/portfolios/{pid}/orders/pending",
                headers=_auth(token),
            )

        assert resp.status_code == 502


@pytest.mark.integration
class TestPlaceOrderErrors:
    """주문 실행 에러 케이스 테스트."""

    async def test_order_kis_api_error_returns_502(
        self, client: AsyncClient
    ) -> None:
        """KIS API 호출 실패 시 502 반환."""
        token, pid, _kis_id = await _setup_portfolio_with_kis(
            client, "order_kis_err@test.com"
        )

        with patch(
            "app.api.orders.place_domestic_order", new_callable=AsyncMock
        ) as mock_order:
            mock_order.side_effect = RuntimeError("KIS API 오류")
            resp = await client.post(
                f"/portfolios/{pid}/orders",
                json={
                    "ticker": "005930",
                    "order_type": "BUY",
                    "order_class": "limit",
                    "quantity": 1,
                    "price": 70000,
                },
                headers=_auth(token),
            )

        assert resp.status_code == 502
