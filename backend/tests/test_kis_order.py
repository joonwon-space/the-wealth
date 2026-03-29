"""KIS 주문 서비스 단위/통합 테스트 (kis_order.py).

place_domestic_order, place_overseas_order, cancel_order, get_pending_orders,
get_orderable_quantity, 계좌 유형별 TR_ID 분기 검증.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx


DUMMY_KEY = "dummy_app_key"
DUMMY_SECRET = "dummy_app_secret"
DUMMY_ACCT = "12345678"
DUMMY_PRDT = "01"


@pytest.fixture(autouse=True)
def mock_kis_token():
    """모든 테스트에서 KIS 토큰 발급을 mock."""
    with patch(
        "app.services.kis_order.get_kis_access_token",
        new_callable=AsyncMock,
        return_value="fake_token",
    ):
        yield


@pytest.fixture(autouse=True)
def mock_cache():
    """Redis cache를 mock으로 대체 (락/레이트리밋 통과)."""
    with patch("app.services.kis_order._cache") as mock_c:
        mock_c.get = AsyncMock(return_value=None)
        mock_c.setex = AsyncMock(return_value=True)
        yield mock_c


# ─── 국내 주문 테스트 ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPlaceDomesticOrder:
    async def test_buy_order_success(self) -> None:
        """국내 매수 주문 성공."""
        from app.services.kis_order import place_domestic_order

        resp_data = {
            "rt_cd": "0",
            "msg1": "주문 완료",
            "output": {"ODNO": "0000000001"},
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-cash"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await place_domestic_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="005930",
                order_type="BUY",
                quantity=10,
                price=Decimal("70000"),
            )

        assert result.status == "pending"
        assert result.order_no == "0000000001"
        assert result.ticker == "005930"
        assert result.order_type == "BUY"

    async def test_sell_order_success(self) -> None:
        """국내 매도 주문 성공."""
        from app.services.kis_order import place_domestic_order

        resp_data = {
            "rt_cd": "0",
            "msg1": "매도 완료",
            "output": {"ODNO": "0000000002"},
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-cash"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await place_domestic_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="005930",
                order_type="SELL",
                quantity=5,
                price=Decimal("72000"),
            )

        assert result.status == "pending"
        assert result.order_type == "SELL"

    async def test_kis_api_error_returns_failed_status(self) -> None:
        """KIS API 오류 코드 (rt_cd != 0) → status=failed."""
        from app.services.kis_order import place_domestic_order

        resp_data = {
            "rt_cd": "1",
            "msg1": "예수금 부족",
            "msg2": "잔고 없음",
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-cash"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await place_domestic_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="005930",
                order_type="BUY",
                quantity=10,
                price=Decimal("70000"),
            )

        assert result.status == "failed"
        assert "예수금 부족" in result.message

    async def test_http_exception_raises_runtime_error(self) -> None:
        """HTTP 오류 시 RuntimeError 발생."""
        from app.services.kis_order import place_domestic_order

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-cash"
            ).mock(return_value=httpx.Response(500, json={}))

            with pytest.raises(RuntimeError, match="국내 주식 주문 실패"):
                await place_domestic_order(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                    ticker="005930",
                    order_type="BUY",
                    quantity=10,
                    price=Decimal("70000"),
                )

    async def test_rate_limit_exceeded_returns_failed(
        self, mock_cache: AsyncMock
    ) -> None:
        """레이트 리밋 초과 시 status=failed."""
        from app.services.kis_order import place_domestic_order

        # Make rate limit check return high count
        mock_cache.get = AsyncMock(return_value="5")

        result = await place_domestic_order(
            app_key=DUMMY_KEY,
            app_secret=DUMMY_SECRET,
            account_no=DUMMY_ACCT,
            account_product_code=DUMMY_PRDT,
            ticker="005930",
            order_type="BUY",
            quantity=10,
            price=Decimal("70000"),
            user_id=123,
        )

        assert result.status == "failed"
        assert "한도 초과" in result.message

    async def test_duplicate_lock_returns_failed(
        self, mock_cache: AsyncMock
    ) -> None:
        """이중 주문 방지 락 존재 시 status=failed."""
        from app.services.kis_order import place_domestic_order

        # Rate limit OK (None), but order lock exists
        call_count = 0

        async def _get_side_effect(key: str) -> str | None:
            nonlocal call_count
            call_count += 1
            if "order_lock" in key:
                return "1"  # Lock exists
            return None  # Rate limit OK

        mock_cache.get = AsyncMock(side_effect=_get_side_effect)

        result = await place_domestic_order(
            app_key=DUMMY_KEY,
            app_secret=DUMMY_SECRET,
            account_no=DUMMY_ACCT,
            account_product_code=DUMMY_PRDT,
            ticker="005930",
            order_type="BUY",
            quantity=10,
            price=Decimal("70000"),
            portfolio_id=1,
        )

        assert result.status == "failed"
        assert "중복 주문 방지" in result.message

    async def test_market_order_uses_ord_dvsn_01(self) -> None:
        """시장가 주문 시 ORD_DVSN=01 로 요청."""
        from app.services.kis_order import place_domestic_order

        captured_body: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            import json
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={
                "rt_cd": "0", "msg1": "OK",
                "output": {"ODNO": "0000000003"},
            })

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-cash"
            ).mock(side_effect=capture_request)

            await place_domestic_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="005930",
                order_type="BUY",
                quantity=10,
                price=Decimal("0"),
                order_class="market",
            )

        assert captured_body.get("ORD_DVSN") == "01"
        assert captured_body.get("ORD_UNPR") == "0"

    async def test_pension_account_uses_correct_tr_id(self) -> None:
        """연금저축 계좌 매수 → TTTC0852U TR_ID 사용."""
        from app.services.kis_order import place_domestic_order

        captured_headers: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json={
                "rt_cd": "0", "msg1": "OK",
                "output": {"ODNO": "0000000004"},
            })

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-cash"
            ).mock(side_effect=capture_request)

            await place_domestic_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="005930",
                order_type="BUY",
                quantity=10,
                price=Decimal("70000"),
                account_type="연금저축",
            )

        assert captured_headers.get("tr_id") == "TTTC0852U"


# ─── 해외 주문 테스트 ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPlaceOverseasOrder:
    async def test_overseas_buy_success(self) -> None:
        """해외 매수 주문 성공."""
        from app.services.kis_order import place_overseas_order

        resp_data = {
            "rt_cd": "0",
            "msg1": "주문 완료",
            "output": {"ODNO": "0000000010"},
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/overseas-stock/v1/trading/order"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await place_overseas_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="AAPL",
                exchange_code="NASD",
                order_type="BUY",
                quantity=5,
                price=Decimal("180.00"),
            )

        assert result.status == "pending"
        assert result.order_no == "0000000010"
        assert result.ticker == "AAPL"

    async def test_overseas_sell_success(self) -> None:
        """해외 매도 주문 성공."""
        from app.services.kis_order import place_overseas_order

        resp_data = {
            "rt_cd": "0",
            "msg1": "매도 완료",
            "output": {"ODNO": "0000000011"},
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/overseas-stock/v1/trading/order"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await place_overseas_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="AAPL",
                exchange_code="NASD",
                order_type="SELL",
                quantity=3,
                price=Decimal("200.00"),
            )

        assert result.status == "pending"
        assert result.order_type == "SELL"

    async def test_overseas_api_error_returns_failed(self) -> None:
        """해외 주문 API 오류 → status=failed."""
        from app.services.kis_order import place_overseas_order

        resp_data = {"rt_cd": "1", "msg1": "해외주식 주문 불가"}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/overseas-stock/v1/trading/order"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await place_overseas_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="AAPL",
                exchange_code="NASD",
                order_type="BUY",
                quantity=1,
                price=Decimal("180.00"),
            )

        assert result.status == "failed"

    async def test_overseas_http_error_raises_runtime_error(self) -> None:
        """HTTP 오류 시 RuntimeError 발생."""
        from app.services.kis_order import place_overseas_order

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/overseas-stock/v1/trading/order"
            ).mock(return_value=httpx.Response(500, json={}))

            with pytest.raises(RuntimeError, match="해외 주식 주문 실패"):
                await place_overseas_order(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                    ticker="AAPL",
                    exchange_code="NASD",
                    order_type="BUY",
                    quantity=1,
                    price=Decimal("180.00"),
                )


# ─── 주문 취소 테스트 ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCancelOrder:
    async def test_cancel_domestic_order_success(self) -> None:
        """국내 주문 취소 성공."""
        from app.services.kis_order import cancel_order

        resp_data = {"rt_cd": "0", "msg1": "취소 완료", "output": {"ODNO": "0000000001"}}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-rvsecncl"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await cancel_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                order_no="0000000001",
                ticker="005930",
                quantity=10,
                price=70000,
            )

        assert result is True

    async def test_cancel_overseas_order_success(self) -> None:
        """해외 주문 취소 성공."""
        from app.services.kis_order import cancel_order

        resp_data = {"rt_cd": "0", "msg1": "취소 완료", "output": {"ODNO": "0000000010"}}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/overseas-stock/v1/trading/order-rvsecncl"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await cancel_order(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                order_no="0000000010",
                ticker="AAPL",
                quantity=5,
                price=180,
                is_overseas=True,
                exchange_code="NASD",
            )

        assert result is True

    async def test_cancel_api_failure_raises_runtime_error(self) -> None:
        """취소 API 오류 시 RuntimeError 발생."""
        from app.services.kis_order import cancel_order

        resp_data = {"rt_cd": "1", "msg1": "취소 불가"}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.post(
                "/uapi/domestic-stock/v1/trading/order-rvsecncl"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            with pytest.raises(RuntimeError, match="주문 취소 실패"):
                await cancel_order(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                    order_no="0000000001",
                    ticker="005930",
                    quantity=10,
                    price=70000,
                )


# ─── 미체결 주문 조회 테스트 ──────────────────────────────────────────────────


@pytest.mark.unit
class TestGetPendingOrders:
    async def test_domestic_pending_orders_success(self) -> None:
        """국내 미체결 주문 조회 성공."""
        from app.services.kis_order import get_pending_orders

        item = {
            "odno": "0000000001",
            "pdno": "005930",
            "prdt_name": "삼성전자",
            "sll_buy_dvsn_cd": "02",  # BUY
            "ord_qty": "10",
            "tot_ccld_qty": "0",
            "ord_unpr": "70000",
            "ord_tmd": "091500",
            "ord_dvsn_cd": "00",  # limit
        }
        resp_data = {"rt_cd": "0", "output1": [item]}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            results = await get_pending_orders(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
            )

        assert len(results) == 1
        order = results[0]
        assert order.ticker == "005930"
        assert order.order_type == "BUY"
        assert order.order_class == "limit"
        assert order.quantity == Decimal("10")
        assert order.remaining_quantity == Decimal("10")

    async def test_domestic_pending_sell_order(self) -> None:
        """국내 매도 미체결 주문 조회."""
        from app.services.kis_order import get_pending_orders

        item = {
            "odno": "0000000002",
            "pdno": "005930",
            "prdt_name": "삼성전자",
            "sll_buy_dvsn_cd": "01",  # SELL
            "ord_qty": "5",
            "tot_ccld_qty": "2",
            "ord_unpr": "72000",
            "ord_tmd": "100000",
            "ord_dvsn_cd": "00",
        }
        resp_data = {"rt_cd": "0", "output1": [item]}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            results = await get_pending_orders(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
            )

        assert results[0].order_type == "SELL"
        assert results[0].filled_quantity == Decimal("2")
        assert results[0].remaining_quantity == Decimal("3")

    async def test_overseas_pending_orders_success(self) -> None:
        """해외 미체결 주문 조회 성공."""
        from app.services.kis_order import get_pending_orders

        item = {
            "odno": "0000000010",
            "pdno": "AAPL",
            "prdt_name": "Apple",
            "sll_buy_dvsn_cd": "02",  # BUY
            "ft_ord_qty": "5",
            "ft_ccld_qty": "0",
            "ft_ord_unpr3": "180.00",
            "ord_tmd": "091500",
        }
        resp_data = {"rt_cd": "0", "output1": [item]}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/overseas-stock/v1/trading/inquire-nccs"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            results = await get_pending_orders(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                is_overseas=True,
            )

        assert len(results) == 1
        assert results[0].ticker == "AAPL"
        assert results[0].order_type == "BUY"

    async def test_api_error_raises_runtime_error(self) -> None:
        """API 오류 시 RuntimeError 발생."""
        from app.services.kis_order import get_pending_orders

        resp_data = {"rt_cd": "1", "msg1": "조회 실패"}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            with pytest.raises(RuntimeError, match="KIS API 오류"):
                await get_pending_orders(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                )

    async def test_empty_output1_returns_empty_list(self) -> None:
        """output1이 빈 경우 빈 리스트 반환."""
        from app.services.kis_order import get_pending_orders

        resp_data = {"rt_cd": "0", "output1": []}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            results = await get_pending_orders(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
            )

        assert results == []


# ─── 주문 가능 수량 조회 테스트 ────────────────────────────────────────────────


@pytest.mark.unit
class TestGetOrderableQuantity:
    async def test_success_returns_orderable_info(self) -> None:
        """주문 가능 수량 조회 성공."""
        from app.services.kis_order import get_orderable_quantity

        resp_data = {
            "rt_cd": "0",
            "output": {
                "psbl_qty": "50",
                "ord_psbl_cash": "3500000",
                "nrcvb_buy_amt": "70000",
            },
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await get_orderable_quantity(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                ticker="005930",
                price=70000,
            )

        assert result.orderable_quantity == Decimal("50")
        assert result.orderable_amount == Decimal("3500000")
        assert result.currency == "KRW"

    async def test_api_error_raises_runtime_error(self) -> None:
        """API 오류 시 RuntimeError 발생."""
        from app.services.kis_order import get_orderable_quantity

        resp_data = {"rt_cd": "1", "msg1": "조회 실패"}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            with pytest.raises(RuntimeError, match="KIS API 오류"):
                await get_orderable_quantity(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                    ticker="005930",
                    price=70000,
                )
