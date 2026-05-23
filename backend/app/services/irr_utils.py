"""불규칙 일자 현금흐름 XIRR (extended internal rate of return) 계산.

`numpy-financial` 패키지에 의존하지 않기 위해 이분법(bisection) 으로 직접
구현. 보유 종목 수십~수백 건 기준 1ms 미만으로 충분히 빠르다.

부호 컨벤션 (투자자 관점):
  - 음수 cashflow = 유출 (매수, 적립, 입금)
  - 양수 cashflow = 유입 (매도, 배당 수령, 평가 종료가)

NPV 공식:
    NPV(r) = Σ cf_i / (1 + r) ** (days_i / 365)
XIRR 은 NPV(r) = 0 인 연복리 r 을 의미.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence


_DAYS_PER_YEAR = 365.0
_MAX_ITER = 200
_TOL = 1e-7
# IRR 탐색 범위. 연 -99% ~ +1000% 면 실투자에서 만나는 모든 케이스를 포함.
_LOW = -0.999999
_HIGH = 10.0


def _npv(rate: float, cashflows: Sequence[tuple[date, float]], anchor: date) -> float:
    total = 0.0
    base = 1.0 + rate
    for d, cf in cashflows:
        days = (d - anchor).days
        total += cf / (base ** (days / _DAYS_PER_YEAR))
    return total


def xirr(cashflows: Sequence[tuple[date, float]]) -> float | None:
    """연복리 IRR 을 반환. 수렴 실패 / 입력 부족 시 None.

    Args:
        cashflows: [(date, amount), ...]. 음수=유출, 양수=유입.

    Returns:
        연 IRR (예: 0.0774 → 연 7.74%). 해가 없거나 cashflow 가 한쪽
        부호로만 구성되면 None.
    """
    if len(cashflows) < 2:
        return None

    has_pos = any(cf > 0 for _, cf in cashflows)
    has_neg = any(cf < 0 for _, cf in cashflows)
    if not (has_pos and has_neg):
        return None

    anchor = min(d for d, _ in cashflows)
    cf_sorted = sorted(cashflows, key=lambda x: x[0])

    low, high = _LOW, _HIGH
    f_low = _npv(low, cf_sorted, anchor)
    f_high = _npv(high, cf_sorted, anchor)

    # 같은 부호면 탐색 구간 안에 해가 없거나 다중 해 — 일단 fail.
    if f_low * f_high > 0:
        return None

    for _ in range(_MAX_ITER):
        mid = (low + high) / 2.0
        f_mid = _npv(mid, cf_sorted, anchor)
        if abs(f_mid) < _TOL or (high - low) < _TOL:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid

    return (low + high) / 2.0
