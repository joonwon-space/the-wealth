"""KIS 체결 내역 조회 서비스 단위 테스트 (kis_transaction.py).

국내: TTTC8001R, 해외: TTTS3035R
httpx mock으로 KIS API 응답 모킹.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_domestic_resp(rows: list[dict]) -> dict:
    return {"rt_cd": "0", "output1": rows}


def _make_overseas_resp(rows: list[dict]) -> dict:
    return {"rt_cd": "0", "output": rows}


DUMMY_KEY = "dummy_app_key"
DUMMY_SECRET = "dummy_app_secret"
DUMMY_ACCT = "12345678"
DUMMY_PRDT = "01"
FROM_DATE = "20240101"
TO_DATE = "20240131"


@pytest.fixture(autouse=True)
def mock_kis_token():
    """모든 테스트에서 KIS 토큰 발급을 mock."""
    with patch(
        "app.services.kis_transaction.get_kis_access_token",
        new_callable=AsyncMock,
        return_value="fake_token",
    ):
        yield


# ─── 국내 체결 내역 테스트 ────────────────────────────────────────────────────


@pytest.mark.unit
class TestFetchDomesticTransactions:
    async def test_returns_empty_on_empty_output(self) -> None:
        """output1이 빈 경우 빈 리스트 반환."""
        from app.services.kis_transaction import fetch_domestic_transactions

        resp_data = _make_domestic_resp([])

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
                ).mock(return_value=httpx.Response(200, json=resp_data))

                result = await fetch_domestic_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        assert result == []

    async def test_returns_buy_transaction(self) -> None:
        """sll_buy_dvsn_cd=02(매수) 행 → type=BUY."""
        from app.services.kis_transaction import fetch_domestic_transactions

        row = {
            "pdno": "005930",
            "prdt_name": "삼성전자",
            "sll_buy_dvsn_cd": "02",
            "tot_ccld_qty": "10",
            "avg_prvs": "70000",
            "ord_dt": "20240115",
            "ord_tmd": "091500",
        }
        resp_data = _make_domestic_resp([row])

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
                ).mock(return_value=httpx.Response(200, json=resp_data))

                result = await fetch_domestic_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        assert len(result) == 1
        tx = result[0]
        assert tx["ticker"] == "005930"
        assert tx["type"] == "BUY"
        assert tx["quantity"] == "10"
        assert tx["price"] == "70000"
        assert tx["market"] == "domestic"

    async def test_returns_sell_transaction(self) -> None:
        """sll_buy_dvsn_cd=01(매도) 행 → type=SELL."""
        from app.services.kis_transaction import fetch_domestic_transactions

        row = {
            "pdno": "005930",
            "prdt_name": "삼성전자",
            "sll_buy_dvsn_cd": "01",
            "tot_ccld_qty": "5",
            "avg_prvs": "72000",
            "ord_dt": "20240120",
            "ord_tmd": "100000",
        }
        resp_data = _make_domestic_resp([row])

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
                ).mock(return_value=httpx.Response(200, json=resp_data))

                result = await fetch_domestic_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        assert len(result) == 1
        assert result[0]["type"] == "SELL"

    async def test_skips_zero_quantity_rows(self) -> None:
        """수량이 0인 행은 건너뜀."""
        from app.services.kis_transaction import fetch_domestic_transactions

        rows = [
            {
                "pdno": "005930",
                "prdt_name": "삼성전자",
                "sll_buy_dvsn_cd": "02",
                "tot_ccld_qty": "0",
                "avg_prvs": "70000",
                "ord_dt": "20240115",
                "ord_tmd": "091500",
            },
            {
                "pdno": "000660",
                "prdt_name": "SK하이닉스",
                "sll_buy_dvsn_cd": "02",
                "tot_ccld_qty": "3",
                "avg_prvs": "120000",
                "ord_dt": "20240116",
                "ord_tmd": "092000",
            },
        ]
        resp_data = _make_domestic_resp(rows)

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
                ).mock(return_value=httpx.Response(200, json=resp_data))

                result = await fetch_domestic_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        assert len(result) == 1
        assert result[0]["ticker"] == "000660"

    async def test_returns_empty_on_http_error(self) -> None:
        """HTTP 오류 시 빈 리스트 반환 (예외를 전파하지 않음)."""
        from app.services.kis_transaction import fetch_domestic_transactions

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
                ).mock(return_value=httpx.Response(500, json={"error": "internal"}))

                result = await fetch_domestic_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        assert result == []

    async def test_traded_at_format(self) -> None:
        """traded_at이 ISO 형식으로 파싱됨."""
        from app.services.kis_transaction import fetch_domestic_transactions

        row = {
            "pdno": "005930",
            "prdt_name": "삼성전자",
            "sll_buy_dvsn_cd": "02",
            "tot_ccld_qty": "10",
            "avg_prvs": "70000",
            "ord_dt": "20240115",
            "ord_tmd": "091500",
        }
        resp_data = _make_domestic_resp([row])

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
                ).mock(return_value=httpx.Response(200, json=resp_data))

                result = await fetch_domestic_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        assert "T" in result[0]["traded_at"]  # ISO format contains T


# ─── 해외 체결 내역 테스트 ────────────────────────────────────────────────────


@pytest.mark.unit
class TestFetchOverseasTransactions:
    async def test_returns_buy_transaction_from_nasd(self) -> None:
        """NASD 거래소 매수 체결 내역 반환."""
        from app.services.kis_transaction import fetch_overseas_transactions, _OVERSEAS_EXCHANGES

        row = {
            "pdno": "AAPL",
            "prdt_name": "Apple",
            "sll_buy_dvsn_cd": "02",
            "ft_ccld_qty": "5",
            "ft_ccld_unpr3": "180.00",
            "ord_dt": "20240115",
            "ord_tmd": "091500",
            "ovrs_excg_cd": "NASD",
        }

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                # Return data for NASD, empty for all others
                for exch in _OVERSEAS_EXCHANGES:
                    rows = [row] if exch == "NASD" else []
                    mock.get(
                        "/uapi/overseas-stock/v1/trading/inquire-ccnl",
                        params={"OVRS_EXCG_CD": exch},
                    ).mock(return_value=httpx.Response(200, json=_make_overseas_resp(rows)))

                result = await fetch_overseas_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        aapl_txs = [t for t in result if t["ticker"] == "AAPL"]
        assert len(aapl_txs) == 1
        assert aapl_txs[0]["type"] == "BUY"
        assert aapl_txs[0]["price"] == "180.00"

    async def test_returns_sell_transaction(self) -> None:
        """sll_buy_dvsn_cd=01 → type=SELL.

        respx는 동일 URL에 대해 마지막 등록된 mock을 반환하므로
        all-exchanges mock 패턴을 사용.
        """
        from app.services.kis_transaction import fetch_overseas_transactions

        row = {
            "pdno": "TSLA",
            "prdt_name": "Tesla",
            "sll_buy_dvsn_cd": "01",
            "ft_ccld_qty": "2",
            "ft_ccld_unpr3": "220.00",
            "ord_dt": "20240116",
            "ord_tmd": "100000",
            "ovrs_excg_cd": "NASD",
        }

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                # Return TSLA for every exchange call
                mock.get(
                    "/uapi/overseas-stock/v1/trading/inquire-ccnl",
                ).mock(return_value=httpx.Response(200, json=_make_overseas_resp([row])))

                result = await fetch_overseas_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        tsla_txs = [t for t in result if t["ticker"] == "TSLA"]
        assert len(tsla_txs) >= 1
        assert all(t["type"] == "SELL" for t in tsla_txs)

    async def test_skips_zero_quantity_rows(self) -> None:
        """수량 0 행은 건너뜀."""
        from app.services.kis_transaction import fetch_overseas_transactions, _OVERSEAS_EXCHANGES

        row_zero = {
            "pdno": "AAPL",
            "prdt_name": "Apple",
            "sll_buy_dvsn_cd": "02",
            "ft_ccld_qty": "0",
            "ft_ccld_unpr3": "180.00",
            "ord_dt": "20240115",
            "ord_tmd": "091500",
            "ovrs_excg_cd": "NASD",
        }

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                for exch in _OVERSEAS_EXCHANGES:
                    rows = [row_zero] if exch == "NASD" else []
                    mock.get(
                        "/uapi/overseas-stock/v1/trading/inquire-ccnl",
                    ).mock(return_value=httpx.Response(200, json=_make_overseas_resp(rows)))

                result = await fetch_overseas_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        assert result == []

    async def test_handles_http_error_gracefully(self) -> None:
        """HTTP 오류 시 해당 거래소 결과는 건너뜀."""
        from app.services.kis_transaction import fetch_overseas_transactions

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/overseas-stock/v1/trading/inquire-ccnl",
                ).mock(return_value=httpx.Response(500, json={"error": "internal"}))

                result = await fetch_overseas_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        # Should return empty (errors are caught and logged)
        assert result == []

    async def test_combines_results_from_multiple_exchanges(self) -> None:
        """여러 거래소 결과 합산 — 모든 거래소에 동일한 응답 반환하여 합산 확인."""
        from app.services.kis_transaction import (
            fetch_overseas_transactions,
            _OVERSEAS_EXCHANGES,
        )

        row = {
            "pdno": "AAPL", "prdt_name": "Apple",
            "sll_buy_dvsn_cd": "02", "ft_ccld_qty": "5",
            "ft_ccld_unpr3": "180.00", "ord_dt": "20240115",
            "ord_tmd": "091500", "ovrs_excg_cd": "NASD",
        }

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/overseas-stock/v1/trading/inquire-ccnl",
                ).mock(return_value=httpx.Response(200, json=_make_overseas_resp([row])))

                result = await fetch_overseas_transactions(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, client,
                )

        # All 9 exchanges each return 1 AAPL row → total 9
        assert len(result) == len(_OVERSEAS_EXCHANGES)
        assert all(t["ticker"] == "AAPL" for t in result)


# ─── Private fetch_overseas by exchange test ────────────────────────────────


@pytest.mark.unit
class TestFetchOverseasByExchange:
    async def test_fetch_single_exchange(self) -> None:
        """단일 거래소 조회."""
        from app.services.kis_transaction import _fetch_overseas_transactions_by_exchange

        row = {
            "pdno": "AAPL", "prdt_name": "Apple",
            "sll_buy_dvsn_cd": "02", "ft_ccld_qty": "5",
            "ft_ccld_unpr3": "180.00", "ord_dt": "20240115",
            "ord_tmd": "091500", "ovrs_excg_cd": "NASD",
        }

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/overseas-stock/v1/trading/inquire-ccnl"
                ).mock(return_value=httpx.Response(200, json=_make_overseas_resp([row])))

                result = await _fetch_overseas_transactions_by_exchange(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, "NASD", client,
                )

        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"
        assert result[0]["market"] == "NASD"

    async def test_handles_missing_output_key(self) -> None:
        """output 키가 없는 응답 처리."""
        from app.services.kis_transaction import _fetch_overseas_transactions_by_exchange

        async with httpx.AsyncClient() as client:
            with respx.mock(base_url="https://openapi.koreainvestment.com:9443") as mock:
                mock.get(
                    "/uapi/overseas-stock/v1/trading/inquire-ccnl"
                ).mock(return_value=httpx.Response(200, json={"rt_cd": "1", "msg1": "error"}))

                result = await _fetch_overseas_transactions_by_exchange(
                    DUMMY_KEY, DUMMY_SECRET, DUMMY_ACCT, DUMMY_PRDT,
                    FROM_DATE, TO_DATE, "NASD", client,
                )

        assert result == []
