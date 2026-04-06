"""Unit tests for analytics metrics calculation functions.

Tests cover _calc_mdd, _calc_cagr, _calc_sharpe from app.api.analytics_metrics.
"""

import math

from app.api.analytics_metrics import _calc_cagr, _calc_mdd, _calc_sharpe


class TestCalcMdd:
    def test_empty_returns_zero(self) -> None:
        assert _calc_mdd([]) == 0.0

    def test_single_value_returns_zero(self) -> None:
        assert _calc_mdd([1000.0]) == 0.0

    def test_monotonic_increase_returns_zero(self) -> None:
        assert _calc_mdd([100.0, 110.0, 120.0, 130.0]) == 0.0

    def test_monotonic_decrease(self) -> None:
        # Peak=100, trough=50 → MDD=50%
        result = _calc_mdd([100.0, 80.0, 60.0, 50.0])
        assert abs(result - 50.0) < 0.01

    def test_recovery_after_drawdown(self) -> None:
        # Peak=100, trough=60 → MDD=40%; then recovery to 110
        result = _calc_mdd([100.0, 80.0, 60.0, 90.0, 110.0])
        assert abs(result - 40.0) < 0.01

    def test_multiple_drawdowns_returns_largest(self) -> None:
        # First dip: 100→80 (20%), second dip: 100→70 (30%) — MDD should be 30%
        result = _calc_mdd([100.0, 80.0, 100.0, 95.0, 70.0, 90.0])
        assert abs(result - 30.0) < 0.01

    def test_result_is_percentage(self) -> None:
        # 100 → 90 is 10% drawdown
        result = _calc_mdd([100.0, 90.0])
        assert abs(result - 10.0) < 0.01


class TestCalcCagr:
    def test_zero_start_returns_none(self) -> None:
        assert _calc_cagr(0.0, 100.0, 1.0) is None

    def test_negative_start_returns_none(self) -> None:
        assert _calc_cagr(-10.0, 100.0, 1.0) is None

    def test_zero_years_returns_none(self) -> None:
        assert _calc_cagr(100.0, 110.0, 0.0) is None

    def test_negative_years_returns_none(self) -> None:
        assert _calc_cagr(100.0, 110.0, -1.0) is None

    def test_one_year_doubles(self) -> None:
        # 100 → 200 in 1 year = 100% CAGR
        result = _calc_cagr(100.0, 200.0, 1.0)
        assert result is not None
        assert abs(result - 100.0) < 0.01

    def test_two_year_exact(self) -> None:
        # 100 → 121 in 2 years = 10% CAGR (1.1^2 = 1.21)
        result = _calc_cagr(100.0, 121.0, 2.0)
        assert result is not None
        assert abs(result - 10.0) < 0.01

    def test_no_growth(self) -> None:
        # 100 → 100 = 0% CAGR
        result = _calc_cagr(100.0, 100.0, 3.0)
        assert result is not None
        assert abs(result - 0.0) < 0.01

    def test_negative_return(self) -> None:
        # 100 → 81 in 2 years = -10% CAGR (0.9^2 = 0.81)
        result = _calc_cagr(100.0, 81.0, 2.0)
        assert result is not None
        assert abs(result - (-10.0)) < 0.01

    def test_result_is_percentage(self) -> None:
        # Result should be expressed as percent (e.g. 10.0, not 0.10)
        result = _calc_cagr(100.0, 110.0, 1.0)
        assert result is not None
        assert result > 1.0  # definitely more than 1%, so it's in % form


class TestCalcSharpe:
    def test_fewer_than_5_returns_none(self) -> None:
        assert _calc_sharpe([0.01, 0.02, 0.01, 0.02]) is None

    def test_zero_std_returns_none(self) -> None:
        # Constant daily return → std=0 → cannot compute Sharpe
        assert _calc_sharpe([0.001] * 10) is None

    def test_positive_excess_return_positive_sharpe(self) -> None:
        # Very high daily return (1%), low risk → positive Sharpe
        # Annual return ~ 1% * 252 = 252%, well above 3.5% risk-free
        returns = [0.01] * 5 + [-0.005] * 5  # some variation
        result = _calc_sharpe(returns)
        assert result is not None
        assert result > 0

    def test_negative_return_negative_sharpe(self) -> None:
        # Consistent negative returns → Sharpe < 0
        returns = [-0.005] * 5 + [-0.01] * 5
        result = _calc_sharpe(returns)
        assert result is not None
        assert result < 0

    def test_result_is_annualized(self) -> None:
        # With known inputs, verify annualization factor sqrt(252) is applied
        # daily_returns all equal 0.001 except one → small but calculable
        daily_returns = [0.001, 0.002, 0.003, 0.001, 0.002, 0.001, 0.002]
        mean = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
        std = math.sqrt(variance)
        annual_return = mean * 252
        annual_std = std * math.sqrt(252)
        risk_free = 0.035
        expected = (annual_return - risk_free) / annual_std

        result = _calc_sharpe(daily_returns)
        assert result is not None
        assert abs(result - expected) < 0.001
