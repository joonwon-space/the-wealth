"""KIS 예수금/잔고 조회 서비스 단위 테스트 (kis_balance.py).

국내 (TTTC8434R), 해외 (TTTS3012R) 예수금 조회,
KIS API 실패 시 에러 전파 검증.
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
        "app.services.kis_balance.get_kis_access_token",
        new_callable=AsyncMock,
        return_value="fake_token",
    ):
        yield


# ─── 국내 예수금 조회 테스트 ─────────────────────────────────────────────────


@pytest.mark.unit
class TestGetDomesticBalance:
    async def test_success_returns_cash_balance(self) -> None:
        """국내 예수금 조회 성공."""
        from app.services.kis_balance import get_cash_balance

        resp_data = {
            "rt_cd": "0",
            "output2": [
                {
                    "tot_evlu_amt": "5000000",
                    "dnca_tot_amt": "1000000",
                    "evlu_pfls_smtl_amt": "500000",
                    "evlu_erng_rt": "11.11",
                }
            ],
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-balance"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await get_cash_balance(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
            )

        assert result.total_cash == Decimal("1000000")
        assert result.available_cash == Decimal("1000000")
        assert result.total_evaluation == Decimal("5000000")
        assert result.total_profit_loss == Decimal("500000")
        assert result.profit_loss_rate == Decimal("11.11")
        assert result.currency == "KRW"

    async def test_api_error_raises_runtime_error(self) -> None:
        """KIS API rt_cd != 0 시 RuntimeError 발생."""
        from app.services.kis_balance import get_cash_balance

        resp_data = {"rt_cd": "1", "msg1": "계좌 오류"}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-balance"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            with pytest.raises(RuntimeError, match="KIS API 오류"):
                await get_cash_balance(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                )

    async def test_http_error_raises_runtime_error(self) -> None:
        """HTTP 오류 시 RuntimeError 발생."""
        from app.services.kis_balance import get_cash_balance

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-balance"
            ).mock(return_value=httpx.Response(500, json={}))

            with pytest.raises(RuntimeError, match="국내 예수금 조회 실패"):
                await get_cash_balance(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                )

    async def test_paper_trading_uses_vttc_tr_id(self) -> None:
        """모의 투자 계좌 시 VTTC8434R TR_ID 사용."""
        from app.services.kis_balance import get_cash_balance

        captured_headers: dict = {}

        def capture(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json={
                "rt_cd": "0",
                "output2": [{
                    "tot_evlu_amt": "1000000",
                    "dnca_tot_amt": "500000",
                    "evlu_pfls_smtl_amt": "0",
                    "evlu_erng_rt": "0",
                }],
            })

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-balance"
            ).mock(side_effect=capture)

            await get_cash_balance(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                is_paper_trading=True,
            )

        assert captured_headers.get("tr_id") == "VTTC8434R"

    async def test_empty_output2_returns_zero_balance(self) -> None:
        """output2가 없거나 비어있을 때 0 값 반환."""
        from app.services.kis_balance import get_cash_balance

        resp_data = {"rt_cd": "0", "output2": []}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/domestic-stock/v1/trading/inquire-balance"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await get_cash_balance(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
            )

        assert result.total_cash == Decimal("0")
        assert result.total_evaluation == Decimal("0")


# ─── 해외 예수금 조회 테스트 ─────────────────────────────────────────────────


@pytest.mark.unit
class TestGetOverseasBalance:
    async def test_success_returns_usd_balance(self) -> None:
        """해외 예수금 조회 성공 — USD 통화 반환."""
        from app.services.kis_balance import get_cash_balance

        resp_data = {
            "rt_cd": "0",
            "output2": {
                "tot_evlu_pfls_amt": "10000",
                "frcr_evlu_pfls_amt": "8000",
                "ovrs_tot_pfls": "1000",
                "frcr_buy_amt_smtl1": "2000",
            },
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/overseas-stock/v1/trading/inquire-balance"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await get_cash_balance(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                is_overseas=True,
            )

        assert result.currency == "USD"
        assert result.total_cash == Decimal("8000")
        assert result.total_evaluation == Decimal("10000")
        assert result.total_profit_loss == Decimal("1000")
        assert result.available_cash == Decimal("6000")  # 8000 - 2000

    async def test_overseas_api_error_raises_runtime_error(self) -> None:
        """해외 API 오류 시 RuntimeError 발생."""
        from app.services.kis_balance import get_cash_balance

        resp_data = {"rt_cd": "1", "msg1": "해외 계좌 오류"}

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/overseas-stock/v1/trading/inquire-balance"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            with pytest.raises(RuntimeError, match="KIS 해외 API 오류"):
                await get_cash_balance(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                    is_overseas=True,
                )

    async def test_overseas_http_error_raises_runtime_error(self) -> None:
        """HTTP 오류 시 RuntimeError 발생."""
        from app.services.kis_balance import get_cash_balance

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/overseas-stock/v1/trading/inquire-balance"
            ).mock(return_value=httpx.Response(500, json={}))

            with pytest.raises(RuntimeError, match="해외 예수금 조회 실패"):
                await get_cash_balance(
                    app_key=DUMMY_KEY,
                    app_secret=DUMMY_SECRET,
                    account_no=DUMMY_ACCT,
                    account_product_code=DUMMY_PRDT,
                    is_overseas=True,
                )

    async def test_overseas_uses_ttts_tr_id(self) -> None:
        """해외 조회 시 TTTS3012R TR_ID 사용."""
        from app.services.kis_balance import get_cash_balance

        captured_headers: dict = {}

        def capture(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json={
                "rt_cd": "0",
                "output2": {
                    "tot_evlu_pfls_amt": "0",
                    "frcr_evlu_pfls_amt": "0",
                    "ovrs_tot_pfls": "0",
                    "frcr_buy_amt_smtl1": "0",
                },
            })

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/overseas-stock/v1/trading/inquire-balance"
            ).mock(side_effect=capture)

            await get_cash_balance(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
                is_overseas=True,
            )

        assert captured_headers.get("tr_id") == "TTTS3012R"
