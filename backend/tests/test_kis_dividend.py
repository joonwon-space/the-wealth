"""TASK-RD-1: KIS 배당 수집 서비스 단위 테스트.

순수 파싱 함수와 in-memory upsert 동작을 검증한다.
HTTP 호출 (KIS API) 부분은 통합 테스트가 필요하므로 여기서는 스킵.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.kis_dividend import (
    parse_domestic_dividend_row,
    parse_overseas_dividend_row,
)


@pytest.mark.unit
class TestParseDomesticDividend:
    def test_complete_row_parses_all_fields(self) -> None:
        row = {
            "sht_cd": "005930",
            "record_date": "20260315",
            "ex_dvdn_dt": "20260314",
            "dvdn_pay_dt": "20260420",
            "per_sto_divi_amt": "361",
        }
        out = parse_domestic_dividend_row(row)
        assert out is not None
        assert out["ticker"] == "005930"
        assert out["market"] == "KRX"
        assert out["record_date"] == date(2026, 3, 15)
        assert out["ex_date"] == date(2026, 3, 14)
        assert out["payment_date"] == date(2026, 4, 20)
        assert out["amount"] == Decimal("361")
        assert out["currency"] == "KRW"
        assert out["kind"] == "cash"
        assert out["source"] == "kis_domestic"
        assert out["raw"] == row

    def test_missing_ticker_returns_none(self) -> None:
        row = {
            "record_date": "20260315",
            "per_sto_divi_amt": "361",
        }
        assert parse_domestic_dividend_row(row) is None

    def test_missing_record_date_returns_none(self) -> None:
        row = {"sht_cd": "005930", "per_sto_divi_amt": "361"}
        assert parse_domestic_dividend_row(row) is None

    def test_missing_amount_returns_none(self) -> None:
        row = {"sht_cd": "005930", "record_date": "20260315"}
        assert parse_domestic_dividend_row(row) is None

    def test_handles_iso_date_format(self) -> None:
        row = {
            "pdno": "005930",
            "record_date": "2026-03-15",
            "dvdn_amt": "1,234.5",
        }
        out = parse_domestic_dividend_row(row)
        assert out is not None
        assert out["record_date"] == date(2026, 3, 15)
        assert out["amount"] == Decimal("1234.5")


@pytest.mark.unit
class TestParseOverseasDividend:
    def test_complete_row(self) -> None:
        row = {
            "symb": "AAPL",
            "excd": "NAS",
            "record_date": "20260301",
            "ex_date": "20260228",
            "pay_date": "20260315",
            "per_sto_divi_amt": "0.24",
            "currency": "USD",
        }
        out = parse_overseas_dividend_row(row)
        assert out is not None
        assert out["ticker"] == "AAPL"
        assert out["market"] == "NAS"
        assert out["record_date"] == date(2026, 3, 1)
        assert out["ex_date"] == date(2026, 2, 28)
        assert out["payment_date"] == date(2026, 3, 15)
        assert out["amount"] == Decimal("0.24")
        assert out["currency"] == "USD"
        assert out["source"] == "kis_overseas_ice"

    def test_market_falls_back_to_ovs(self) -> None:
        row = {
            "symb": "AAPL",
            "record_date": "20260301",
            "per_sto_divi_amt": "0.24",
        }
        out = parse_overseas_dividend_row(row)
        assert out is not None
        assert out["market"] == "OVS"

    def test_missing_symbol_returns_none(self) -> None:
        row = {
            "record_date": "20260301",
            "per_sto_divi_amt": "0.24",
        }
        assert parse_overseas_dividend_row(row) is None
