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

    async def test_prvs_rcdl_excc_amt_is_used_when_present(self) -> None:
        """D+2 가수도 정산금액(prvs_rcdl_excc_amt)이 있으면 이 값을 그대로 사용."""
        from app.services.kis_balance import get_cash_balance

        # ISA/일반/연금/IRP 모두 KIS가 직접 계산한 D+2 가용 예수금을 우선 사용.
        resp_data = {
            "rt_cd": "0",
            "output2": [
                {
                    "tot_evlu_amt": "20000000",
                    "dnca_tot_amt": "12827689",
                    "nxdy_excc_amt": "3529699",
                    "prvs_rcdl_excc_amt": "836587",
                    "thdt_buy_amt": "2693000",
                    "thdt_sll_amt": "0",
                    "evlu_pfls_smtl_amt": "0",
                    "evlu_erng_rt": "0",
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

        # KIS가 직접 계산한 D+2 = 836,587 그대로
        assert result.available_cash == Decimal("836587")

    async def test_nxdy_falls_back_to_buy_amount_subtraction(self) -> None:
        """prvs_rcdl 미제공 시 nxdy - thdt_buy + thdt_sll 산식으로 보정."""
        from app.services.kis_balance import get_cash_balance

        resp_data = {
            "rt_cd": "0",
            "output2": [
                {
                    "tot_evlu_amt": "20000000",
                    "dnca_tot_amt": "12827689",
                    "nxdy_excc_amt": "3529699",
                    # prvs_rcdl_excc_amt 미제공
                    "thdt_buy_amt": "2693000",
                    "thdt_sll_amt": "0",
                    "evlu_pfls_smtl_amt": "0",
                    "evlu_erng_rt": "0",
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

        # 3,529,699 - 2,693,000 + 0 = 836,699 (수수료/세금 제외, KIS 직접계산보다 ~100원 차이)
        assert result.available_cash == Decimal("836699")

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


# ─── 해외 현재잔고(CTRP6504R) USD 매수가능액 추출 테스트 ──────────────────────


@pytest.mark.unit
class TestGetOverseasPresentBalance:
    async def test_uses_frcr_drwg_psbl_amt_1_for_usd_orderable(self) -> None:
        """USD 매수가능액은 frcr_drwg_psbl_amt_1(외화인출가능금액)을 사용한다.

        frcr_dncl_amt_2(단순 외화잔액)는 매수 결제 약정금이 차감되지 않아
        사용자에게 과대 표시된다. 진짜 매수가능액은 KIS의 inquire-psamount
        `ord_psbl_frcr_amt`와 동일한 frcr_drwg_psbl_amt_1을 써야 한다.
        """
        from app.services.kis_balance import get_overseas_present_balance

        resp_data = {
            "rt_cd": "0",
            "output2": [
                {
                    "crcy_cd": "USD",
                    "frcr_dncl_amt_2": "883.95",      # 단순 잔액
                    "frcr_buy_amt_smtl": "761.77",    # 매수 결제 약정
                    "frcr_drwg_psbl_amt_1": "122.18", # 실제 매수가능 (= 883.95 - 761.77)
                    "frst_bltn_exrt": "1503.20",
                },
            ],
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/overseas-stock/v1/trading/inquire-present-balance"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await get_overseas_present_balance(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
            )

        # 단순 잔액이 아닌 매수가능액으로 반환
        assert result.usd_cash == Decimal("122.18")
        assert result.usd_krw_rate == Decimal("1503.20")

    async def test_falls_back_to_frcr_dncl_amt_2_when_drwg_missing(self) -> None:
        """frcr_drwg_psbl_amt_1 미제공 시 frcr_dncl_amt_2로 fallback."""
        from app.services.kis_balance import get_overseas_present_balance

        resp_data = {
            "rt_cd": "0",
            "output2": [
                {
                    "crcy_cd": "USD",
                    "frcr_dncl_amt_2": "500.00",
                    # frcr_drwg_psbl_amt_1 미제공
                    "frst_bltn_exrt": "1500.00",
                },
            ],
        }

        with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
            mock.get(
                "/uapi/overseas-stock/v1/trading/inquire-present-balance"
            ).mock(return_value=httpx.Response(200, json=resp_data))

            result = await get_overseas_present_balance(
                app_key=DUMMY_KEY,
                app_secret=DUMMY_SECRET,
                account_no=DUMMY_ACCT,
                account_product_code=DUMMY_PRDT,
            )

        assert result.usd_cash == Decimal("500.00")
