"""xirr 단위 테스트.

DB 의존 없음. `pytest -m unit` 로 격리 실행 가능.
"""

from datetime import date

import pytest

from app.services.irr_utils import xirr


@pytest.mark.unit
class TestXirr:
    def test_returns_none_for_empty(self) -> None:
        assert xirr([]) is None

    def test_returns_none_for_single_cashflow(self) -> None:
        assert xirr([(date(2024, 1, 1), -1000.0)]) is None

    def test_returns_none_when_all_same_sign(self) -> None:
        # 유출만 있고 유입 없음 → 해 없음
        assert xirr([
            (date(2024, 1, 1), -1000.0),
            (date(2025, 1, 1), -500.0),
        ]) is None

    def test_simple_double_in_one_year(self) -> None:
        # -100 투입 후 365일 뒤 +200 → 정확히 +100%
        # (2025-01-01 ~ 2026-01-01 은 정확히 365일)
        rate = xirr([
            (date(2025, 1, 1), -100.0),
            (date(2026, 1, 1), 200.0),
        ])
        assert rate is not None
        assert rate == pytest.approx(1.0, abs=1e-4)

    def test_seven_percent_compound(self) -> None:
        # -1000 → 365일 뒤 +1070 → 연 7%
        rate = xirr([
            (date(2025, 1, 1), -1000.0),
            (date(2026, 1, 1), 1070.0),
        ])
        assert rate is not None
        assert rate == pytest.approx(0.07, abs=1e-4)

    def test_periodic_contributions(self) -> None:
        # 4년간 매년 -1000 적립 후 마지막 시점 +4750.74 ≈ 연 7% 복리.
        # 윤년 포함이라 정확 7% 아닐 수 있어 tolerance 넉넉히.
        rate = xirr([
            (date(2021, 1, 1), -1000.0),
            (date(2022, 1, 1), -1000.0),
            (date(2023, 1, 1), -1000.0),
            (date(2024, 1, 1), -1000.0),
            (date(2025, 1, 1), 4750.74),
        ])
        assert rate is not None
        assert rate == pytest.approx(0.07, abs=2e-2)

    def test_negative_return(self) -> None:
        # -1000 → 365일 뒤 +500 → 연 -50%
        rate = xirr([
            (date(2025, 1, 1), -1000.0),
            (date(2026, 1, 1), 500.0),
        ])
        assert rate is not None
        assert rate == pytest.approx(-0.5, abs=1e-4)

    def test_irregular_dates(self) -> None:
        # 불규칙 일자: 18개월 사이 +50% 수익.
        # -1000 → 18개월 뒤 +1500 ≈ 연 30~32% 수준.
        rate = xirr([
            (date(2025, 1, 1), -1000.0),
            (date(2026, 7, 1), 1500.0),
        ])
        assert rate is not None
        assert 0.2 < rate < 0.4
