"""연도별 수익률 (MWR/XIRR) 계산 서비스.

transactions(매수/매도 현금흐름) + price_snapshots(연말 평가) +
dividends(배당 수령) 를 모두 KRW 로 환산한 뒤 XIRR 로 연간/누적
금액가중 수익률을 산출.

부호 컨벤션 (`irr_utils.xirr` 와 일치):
  - 음수 = 유출 (매수, 적립)
  - 양수 = 유입 (매도, 배당, 평가종료)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ticker import is_domestic
from app.models.dividend import Dividend
from app.models.fx_rate_snapshot import FxRateSnapshot
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.transaction import Transaction
from app.services.fx_utils import forward_fill_rates
from app.services.irr_utils import xirr


# USD/KRW 환율 모를 때의 안전 fallback.
# fx_rate_snapshots 가 비어있는 초창기 사용자만 영향.
_FX_FALLBACK = 1350.0


@dataclass(frozen=True)
class _Cashflow:
    """KRW 환산 cashflow. 음수=유출, 양수=유입."""

    when: date
    amount_krw: float


def _resolve_fx_map(
    fx_snapshots: Sequence[FxRateSnapshot],
    dates_iso: list[str],
) -> dict[str, float]:
    """전체 일자에 대해 USD→KRW 환율 forward-fill."""
    if not dates_iso:
        return {}
    return forward_fill_rates(fx_snapshots, sorted(set(dates_iso)), _FX_FALLBACK)


def _year_last_business_date(year: int, available_dates: set[date]) -> Optional[date]:
    """해당 연도 내 가장 늦은 price_snapshot 날짜를 반환.

    12/31 일 거래가 없을 수 있어 단순 ≤12/31 중 max 로 잡는다.
    """
    candidates = [d for d in available_dates if d.year == year]
    if not candidates:
        return None
    return max(candidates)


def _convert_to_krw(
    amount_native: float,
    ticker: str,
    on_date: date,
    fx_map: dict[str, float],
) -> float:
    if is_domestic(ticker):
        return amount_native
    rate = fx_map.get(on_date.isoformat(), _FX_FALLBACK)
    return amount_native * rate


def _convert_dividend_to_krw(
    amount: float,
    currency: str,
    on_date: date,
    fx_map: dict[str, float],
) -> float:
    if currency == "KRW":
        return amount
    rate = fx_map.get(on_date.isoformat(), _FX_FALLBACK)
    return amount * rate


async def compute_annual_returns(
    db: AsyncSession,
    user_id: int,
    birth_year: Optional[int],
) -> list[dict]:
    """연도별 IRR/평가/적립/배당 리스트를 반환.

    Returns:
        각 dict 는 `schemas.analytics.AnnualReturn` 필드와 동일.
        거래 내역이 없으면 빈 리스트.
    """
    # 1. 사용자 포트폴리오와 거래 내역 로드.
    port_result = await db.execute(
        select(Portfolio.id).where(Portfolio.user_id == user_id)
    )
    portfolio_ids = [row[0] for row in port_result.all()]
    if not portfolio_ids:
        return []

    tx_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id.in_(portfolio_ids),
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.traded_at)
    )
    transactions = list(tx_result.scalars().all())
    if not transactions:
        return []

    tickers = {tx.ticker for tx in transactions}

    # 2. price_snapshots — 보유 종목 전체 기간.
    snap_result = await db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker.in_(tickers))
        .order_by(PriceSnapshot.snapshot_date)
    )
    snapshots = list(snap_result.scalars().all())

    # 3. FX snapshots — forward-fill 용.
    fx_result = await db.execute(
        select(FxRateSnapshot).order_by(FxRateSnapshot.snapshot_date)
    )
    fx_snapshots = list(fx_result.scalars().all())

    # 4. 배당 (보유 ticker 중 payment_date 가 있는 것만).
    div_result = await db.execute(
        select(Dividend).where(
            Dividend.ticker.in_(tickers),
            Dividend.payment_date.is_not(None),
        )
    )
    dividends = list(div_result.scalars().all())

    # 환율 적용에 필요한 모든 일자 모으기.
    fx_dates_needed: set[str] = set()
    for tx in transactions:
        if not is_domestic(tx.ticker):
            fx_dates_needed.add(tx.traded_at.date().isoformat())
    for snap in snapshots:
        if not is_domestic(snap.ticker):
            fx_dates_needed.add(snap.snapshot_date.isoformat())
    for d in dividends:
        if d.currency != "KRW" and d.payment_date is not None:
            fx_dates_needed.add(d.payment_date.isoformat())

    fx_map = _resolve_fx_map(fx_snapshots, sorted(fx_dates_needed))

    # 5. KRW cashflow 시계열 (매수=음수, 매도=양수, 배당=양수).
    cashflows: list[_Cashflow] = []
    tx_by_year: dict[int, float] = defaultdict(float)  # 순 매입(BUY-SELL) KRW
    qty_by_ticker_cumulative: dict[str, float] = defaultdict(float)
    # (year, ticker) → 연말까지 누적 수량 — 평가에 사용.
    # 종가 곱은 별도 단계에서.

    for tx in transactions:
        d = tx.traded_at.date()
        qty = float(tx.quantity)
        price = float(tx.price)
        gross_native = qty * price
        gross_krw = _convert_to_krw(gross_native, tx.ticker, d, fx_map)
        if tx.type == "BUY":
            cashflows.append(_Cashflow(d, -gross_krw))
            tx_by_year[d.year] += gross_krw
            qty_by_ticker_cumulative[tx.ticker] += qty
        elif tx.type == "SELL":
            cashflows.append(_Cashflow(d, gross_krw))
            tx_by_year[d.year] -= gross_krw
            qty_by_ticker_cumulative[tx.ticker] -= qty
        # 그 외 타입은 무시.

    div_by_year: dict[int, float] = defaultdict(float)
    div_cashflows: list[_Cashflow] = []
    for div in dividends:
        if div.payment_date is None:
            continue
        amt_krw = _convert_dividend_to_krw(
            float(div.amount), div.currency, div.payment_date, fx_map
        )
        div_by_year[div.payment_date.year] += amt_krw
        div_cashflows.append(_Cashflow(div.payment_date, amt_krw))

    # 6. 연말 EOP 평가 계산.
    # snapshot 보유 일자 집합 (ticker 무관, 합집합).
    snapshot_dates_by_ticker: dict[str, dict[date, float]] = defaultdict(dict)
    for snap in snapshots:
        snapshot_dates_by_ticker[snap.ticker][snap.snapshot_date] = float(snap.close)
    all_snapshot_dates: set[date] = set()
    for per_ticker in snapshot_dates_by_ticker.values():
        all_snapshot_dates.update(per_ticker.keys())

    # 거래/배당이 발생한 모든 연도 (없으면 평가도 의미 없음).
    first_year = transactions[0].traded_at.date().year
    last_year = date.today().year
    years = list(range(first_year, last_year + 1))

    # ticker 별로 연도 → 누적 quantity 트리.
    ticker_qty_by_year: dict[str, dict[int, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for tx in transactions:
        y = tx.traded_at.date().year
        q = float(tx.quantity) * (1 if tx.type == "BUY" else -1 if tx.type == "SELL" else 0)
        ticker_qty_by_year[tx.ticker][y] += q

    def _cumulative_qty(ticker: str, year: int) -> float:
        total = 0.0
        for y, q in ticker_qty_by_year[ticker].items():
            if y <= year:
                total += q
        return max(total, 0.0)

    eop_value_by_year: dict[int, float] = {}
    eop_date_by_year: dict[int, date] = {}
    for year in years:
        eop_date = _year_last_business_date(year, all_snapshot_dates)
        if eop_date is None:
            continue
        total_krw = 0.0
        for ticker in tickers:
            qty = _cumulative_qty(ticker, year)
            if qty <= 0:
                continue
            # 해당 연도 내 ticker 의 마지막 종가 (없으면 그 이전 가장 최근).
            ticker_dates = sorted(snapshot_dates_by_ticker[ticker].keys())
            relevant = [d for d in ticker_dates if d <= eop_date]
            if not relevant:
                continue
            close_native = snapshot_dates_by_ticker[ticker][relevant[-1]]
            close_krw = _convert_to_krw(close_native * qty, ticker, eop_date, fx_map)
            total_krw += close_krw
        eop_value_by_year[year] = total_krw
        eop_date_by_year[year] = eop_date

    # 7. 연도별 IRR 계산.
    all_cashflows = sorted(cashflows + div_cashflows, key=lambda c: c.when)
    annual_results: list[dict] = []
    prev_eop = 0.0
    for year in years:
        if year not in eop_value_by_year:
            # 평가 데이터 없음 → 행 생성 안 함.
            continue
        eop = eop_value_by_year[year]
        eop_date = eop_date_by_year[year]
        bop = prev_eop
        contrib = tx_by_year.get(year, 0.0)
        divs = div_by_year.get(year, 0.0)
        pnl = eop - bop - contrib + divs

        # 1년 IRR: bop 를 음수 유출, 연중 cashflow, eop 를 양수 유입.
        year_flows: list[tuple[date, float]] = []
        if bop > 0:
            year_flows.append((date(year, 1, 1), -bop))
        for cf in all_cashflows:
            if cf.when.year == year:
                year_flows.append((cf.when, cf.amount_krw))
        year_flows.append((eop_date, eop))
        irr_year = xirr(year_flows)

        # 누적 IRR: 최초 매수일부터 현재 EOP 까지 전체 cashflow + eop.
        cum_flows: list[tuple[date, float]] = [
            (cf.when, cf.amount_krw) for cf in all_cashflows if cf.when <= eop_date
        ]
        cum_flows.append((eop_date, eop))
        irr_cum = xirr(cum_flows)

        age = (year - birth_year) if birth_year else None
        annual_results.append({
            "year": year,
            "age": age,
            "bop_value_krw": round(bop, 2),
            "contributions_krw": round(contrib, 2),
            "dividends_krw": round(divs, 2),
            "eop_value_krw": round(eop, 2),
            "pnl_amount_krw": round(pnl, 2),
            "irr_year": round(irr_year, 6) if irr_year is not None else None,
            "irr_cumulative": round(irr_cum, 6) if irr_cum is not None else None,
        })
        prev_eop = eop

    return annual_results


def simulate_retirement(params: dict) -> list[dict]:
    """은퇴 시뮬레이션 순계산.

    매년 ``eop = bop * (1 + rate) + flow`` 적용.
    `flow` = 적립(+) / 인출(-).
    """
    current_age = params["current_age"]
    end_age = params["end_age"]
    retirement_age = params["retirement_age"]
    rate = params["expected_return_rate"]
    contrib = params["annual_contribution_krw"]
    withdraw = params["annual_withdrawal_krw"]
    bop = params["current_value_krw"]
    start_year = date.today().year

    points: list[dict] = []
    for offset, age in enumerate(range(current_age, end_age + 1)):
        flow = contrib if age < retirement_age else -withdraw
        return_amount = bop * rate
        eop = bop + return_amount + flow
        points.append({
            "age": age,
            "year": start_year + offset,
            "flow_krw": round(flow, 2),
            "return_amount_krw": round(return_amount, 2),
            "eop_value_krw": round(eop, 2),
        })
        bop = max(eop, 0.0)  # 잔고 음수 방지 (인출 단계 자산 소진).
    return points
