"""투자 성과 지표 API — metrics, monthly-returns, sector-allocation."""

import asyncio
import json
import math
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._etag import etag_response
from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.core.ticker import is_domestic
from app.services.kis_price import _cache_price, _get_cached_price, get_cached_fx_rate
from app.services.price_snapshot import fetch_domestic_price_detail
from app.services.kis_price import fetch_overseas_price_detail
from app.data.sector_map import get_sector
from app.schemas.analytics import MonthlyReturn, SectorAllocation
from app.services.analytics_utils import (
    ANALYTICS_CACHE_TTL,
    analytics_key,
    get_analytics_cache,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)

_RISK_FREE_RATE = 0.035  # 연 3.5% (국고채 기준)


def _calc_mdd(values: list[float]) -> float:
    """최대 낙폭(MDD) 계산."""
    if len(values) < 2:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100  # %


def _calc_cagr(start: float, end: float, years: float) -> Optional[float]:
    """CAGR (연복리 수익률) 계산."""
    if start <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100  # %


def _calc_sharpe(daily_returns: list[float]) -> Optional[float]:
    """샤프 비율 계산 (일별 수익률 기반, 연 환산)."""
    if len(daily_returns) < 5:
        return None
    n = len(daily_returns)
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / n
    std = math.sqrt(variance)
    if std == 0:
        return None
    annual_return = mean * 252
    annual_std = std * math.sqrt(252)
    return (annual_return - _RISK_FREE_RATE) / annual_std


async def _fetch_analytics_prices(
    holdings: list[Holding],
    acct: Optional[KisAccount],
) -> dict[str, Optional[Decimal]]:
    """보유 종목의 현재가를 KIS API에서 조회한다. 실패 시 캐시 값 사용."""
    ticker_to_market: dict[str, str] = {
        h.ticker: (h.market or "NAS") for h in holdings if not is_domestic(h.ticker)
    }
    domestic_tickers = [h.ticker for h in holdings if is_domestic(h.ticker)]
    overseas_tickers = [h.ticker for h in holdings if not is_domestic(h.ticker)]
    tickers = domestic_tickers + overseas_tickers
    current_prices: dict[str, Optional[Decimal]] = {}

    if acct:
        try:
            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)
            async with httpx.AsyncClient(timeout=10.0) as client:
                all_details = await asyncio.gather(
                    *[fetch_domestic_price_detail(t, app_key, app_secret, client) for t in domestic_tickers],
                    *[fetch_overseas_price_detail(t, ticker_to_market[t], app_key, app_secret, client) for t in overseas_tickers],
                    return_exceptions=True,
                )
            for ticker, detail in zip(tickers, all_details):
                if detail and not isinstance(detail, Exception):
                    current_prices[ticker] = detail.current
                    await _cache_price(ticker, detail.current)
                else:
                    cached_price = await _get_cached_price(ticker)
                    if cached_price is not None:
                        current_prices[ticker] = cached_price
        except Exception as e:
            logger.warning("Failed to fetch prices for metrics: %s", e)
            fallback_results = await asyncio.gather(*[_get_cached_price(t) for t in tickers], return_exceptions=True)
            for ticker, cached_price in zip(tickers, fallback_results):
                if cached_price is not None and not isinstance(cached_price, Exception):
                    current_prices[ticker] = cached_price

    return current_prices


def _compute_holding_pnl(
    holdings: list[Holding],
    current_prices: dict[str, Optional[Decimal]],
) -> tuple[float, float]:
    """보유 종목 현재가 기반 총 투자금액과 현재 가치를 반환한다."""
    total_invested = sum(float(h.quantity) * float(h.avg_price) for h in holdings)
    total_current = sum(
        float(h.quantity) * float(current_prices.get(h.ticker) or h.avg_price)
        for h in holdings
    )
    return total_invested, total_current


_EMPTY_METRICS = {"total_return_rate": None, "cagr": None, "mdd": None, "sharpe_ratio": None}


@router.get("/metrics")
@limiter.limit("30/minute")
async def get_metrics(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FastAPIResponse:
    """포트폴리오 성과 지표 계산.

    Returns: total_return_rate, cagr, mdd, sharpe_ratio (ETag/304 적용).
    """
    _cache = get_analytics_cache()
    cache_key = analytics_key(current_user.id, "metrics")
    cached = await _cache.get(cache_key)
    if cached:
        return etag_response(request, json.loads(cached))

    # 보유 종목 조회
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    if not portfolio_ids:
        return etag_response(request, _EMPTY_METRICS)

    # 보유 종목 + KIS 계좌를 병렬로 조회 (독립적 쿼리)
    hold_result, acct_result = await asyncio.gather(
        db.execute(select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))),
        db.execute(select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)),
    )
    holdings = hold_result.scalars().all()
    if not holdings:
        return etag_response(request, _EMPTY_METRICS)

    acct = acct_result.scalar_one_or_none()

    current_prices = await _fetch_analytics_prices(list(holdings), acct)
    tickers = [h.ticker for h in holdings]
    total_invested, total_current = _compute_holding_pnl(list(holdings), current_prices)

    if total_invested <= 0:
        return etag_response(request, _EMPTY_METRICS)

    total_return_rate = (total_current - total_invested) / total_invested * 100

    # price_snapshots 기반 일별 포트폴리오 가치 시계열 계산 (최근 1년 데이터만)
    metrics_cutoff = date_type.today() - timedelta(days=365)
    snap_result = await db.execute(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.ticker.in_(tickers),
            PriceSnapshot.snapshot_date >= metrics_cutoff,
        )
        .order_by(PriceSnapshot.snapshot_date)
    )
    snapshots = snap_result.scalars().all()

    # 날짜별 {ticker: close} 맵
    date_ticker_map: dict[str, dict[str, float]] = {}
    for snap in snapshots:
        d = snap.snapshot_date.isoformat()
        if d not in date_ticker_map:
            date_ticker_map[d] = {}
        date_ticker_map[d][snap.ticker] = float(snap.close)

    # forward-fill + backward-fill (analytics_history.py와 동일 패턴):
    # 일부 ticker가 특정 날짜에 PriceSnapshot이 없으면 직전 값을 forward-fill
    # 하고, 첫 등장 이전 날짜는 첫 close로 backward-fill 한다. 그렇지 않으면
    # 누락 ticker가 있는 날짜의 portfolio value 가 비정상적으로 작아 CAGR /
    # MDD 가 spuriously 큰 값으로 계산된다 (peak 대비 99% drawdown 등).
    holding_qty: dict[str, float] = {}
    for h in holdings:
        holding_qty[h.ticker] = holding_qty.get(h.ticker, 0.0) + float(h.quantity)
    first_close: dict[str, float] = {}
    for snap in snapshots:
        if snap.ticker not in first_close:
            first_close[snap.ticker] = float(snap.close)

    last_close: dict[str, float] = {}
    portfolio_date_values: list[tuple[str, float]] = []
    for date_str in sorted(date_ticker_map.keys()):
        for t, close in date_ticker_map[date_str].items():
            last_close[t] = close
        effective = {**first_close, **last_close}
        value = sum(holding_qty[t] * effective[t] for t in tickers if t in effective)
        if value > 0:
            portfolio_date_values.append((date_str, value))

    portfolio_values = [v for _, v in portfolio_date_values]

    # 일별 수익률
    daily_returns: list[float] = []
    for i in range(1, len(portfolio_values)):
        prev = portfolio_values[i - 1]
        if prev > 0:
            daily_returns.append((portfolio_values[i] - prev) / prev)

    # CAGR: 실제 날짜 범위 기반. 90일 미만이면 연복리 외삽이 신뢰성 낮음
    # (예: 41일 +17% → CAGR 290%) — None 반환해 UI 가 "데이터 부족" 폴백.
    cagr: Optional[float] = None
    if portfolio_date_values:
        start_date = date_type.fromisoformat(portfolio_date_values[0][0])
        end_date = date_type.fromisoformat(portfolio_date_values[-1][0])
        days = (end_date - start_date).days
        if days >= 90:
            years = days / 365.25
            cagr = _calc_cagr(portfolio_date_values[0][1], total_current, years)

    mdd = _calc_mdd(portfolio_values + [total_current]) if portfolio_values else 0.0
    sharpe = _calc_sharpe(daily_returns)

    result = {
        "total_return_rate": round(total_return_rate, 2),
        "cagr": round(cagr, 2) if cagr is not None else None,
        "mdd": round(mdd, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
    }
    await _cache.setex(cache_key, ANALYTICS_CACHE_TTL, json.dumps(result))
    return etag_response(request, result)


@router.get("/monthly-returns", response_model=list[MonthlyReturn])
@limiter.limit("30/minute")
async def get_monthly_returns(
    request: Request,
    since: Optional[date_type] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FastAPIResponse:
    """월별 포트폴리오 수익률 계산 (ETag/304 적용).

    price_snapshots에서 각 월의 마지막 거래일 종가를 취합하여
    전월 대비 수익률을 반환한다.

    since: 조회 시작일 (기본값: 오늘 - 365일). 장기 조회 시 명시적으로 지정 가능.
    """
    cutoff = since if since is not None else date_type.today() - timedelta(days=365)

    _cache = get_analytics_cache()
    cache_key = analytics_key(current_user.id, f"monthly-returns:{cutoff.isoformat()}")
    cached = await _cache.get(cache_key)
    if cached:
        return etag_response(request, json.loads(cached))

    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    if not portfolio_ids:
        return etag_response(request, [])

    hold_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    holdings = hold_result.scalars().all()
    if not holdings:
        return etag_response(request, [])

    tickers = list({h.ticker for h in holdings})
    holding_map = {h.ticker: h for h in holdings}

    snap_result = await db.execute(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.ticker.in_(tickers),
            PriceSnapshot.snapshot_date >= cutoff,
        )
        .order_by(PriceSnapshot.snapshot_date)
    )
    snapshots = snap_result.scalars().all()
    if not snapshots:
        return etag_response(request, [])

    # 날짜별 {ticker: close} 맵 구축
    date_ticker_map: dict[str, dict[str, float]] = {}
    for snap in snapshots:
        d = snap.snapshot_date.isoformat()
        if d not in date_ticker_map:
            date_ticker_map[d] = {}
        date_ticker_map[d][snap.ticker] = float(snap.close)

    # 월별 {ticker: last_close} 맵 — 같은 월 내 더 늦은 날짜가 덮어쓴다.
    # 이전 구현은 "월 마지막 날짜의 부분 합계"를 비교했는데, 일부 티커만
    # 스냅샷이 있는 날에 합계가 작아져 다음 달 -100% 같은 가짜 손실이
    # 발생했다. 티커별로 인접 월의 종가를 비교한 뒤 현재 보유 가치로
    # 가중평균하면 부분 커버리지 영향을 받지 않는다.
    month_ticker_close: dict[str, dict[str, float]] = {}
    for date_str in sorted(date_ticker_map.keys()):
        month_key = date_str[:7]  # "YYYY-MM"
        bucket = month_ticker_close.setdefault(month_key, {})
        for ticker, close in date_ticker_map[date_str].items():
            if ticker in holding_map:
                bucket[ticker] = close

    if len(month_ticker_close) < 2:
        return etag_response(request, [])

    sorted_months = sorted(month_ticker_close.keys())
    monthly_returns: list[MonthlyReturn] = []
    for i in range(1, len(sorted_months)):
        prev_key = sorted_months[i - 1]
        curr_key = sorted_months[i]
        prev_closes = month_ticker_close[prev_key]
        curr_closes = month_ticker_close[curr_key]

        weighted_sum = 0.0
        weight_total = 0.0
        for ticker, holding in holding_map.items():
            prev_close = prev_closes.get(ticker)
            curr_close = curr_closes.get(ticker)
            if prev_close is None or curr_close is None or prev_close <= 0:
                continue
            ticker_return = (curr_close - prev_close) / prev_close
            weight = float(holding.quantity) * curr_close
            weighted_sum += ticker_return * weight
            weight_total += weight

        if weight_total > 0:
            return_rate = (weighted_sum / weight_total) * 100
            year, month = int(curr_key[:4]), int(curr_key[5:7])
            monthly_returns.append(
                MonthlyReturn(year=year, month=month, return_rate=round(return_rate, 2))
            )

    payload = [r.model_dump() for r in monthly_returns]
    await _cache.setex(cache_key, ANALYTICS_CACHE_TTL, json.dumps(payload))
    return etag_response(request, payload)


@router.get("/sector-allocation", response_model=list[SectorAllocation])
@limiter.limit("30/minute")
async def get_sector_allocation(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FastAPIResponse:
    """보유 종목의 섹터별 자산 배분 반환 (ETag/304 적용).

    평균 매입가 기준으로 섹터별 투자 금액 비중을 계산한다.
    현재가 조회 없이 빠르게 응답한다.
    """
    _cache = get_analytics_cache()
    cache_key = analytics_key(current_user.id, "sector-allocation")
    cached = await _cache.get(cache_key)
    if cached:
        return etag_response(request, json.loads(cached))

    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    if not portfolio_ids:
        return etag_response(request, [])

    hold_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    holdings = hold_result.scalars().all()
    if not holdings:
        return etag_response(request, [])

    # 해외주식 USD → KRW 환산을 위해 캐시에서 환율 조회
    usd_krw = await get_cached_fx_rate()

    sector_values: dict[str, float] = {}
    for h in holdings:
        sector = get_sector(h.ticker)
        value_local = float(h.quantity) * float(h.avg_price)
        # 해외주식(6자리 숫자가 아닌 ticker)은 USD → KRW 환산
        value = value_local * usd_krw if not is_domestic(h.ticker) else value_local
        sector_values[sector] = sector_values.get(sector, 0.0) + value

    total = sum(sector_values.values())
    if total <= 0:
        return etag_response(request, [])

    result = [
        SectorAllocation(
            sector=sector,
            value=round(value, 0),
            weight=round(value / total * 100, 1),
        )
        for sector, value in sorted(sector_values.items(), key=lambda x: x[1], reverse=True)
    ]
    payload = [r.model_dump() for r in result]
    await _cache.setex(cache_key, ANALYTICS_CACHE_TTL, json.dumps(payload))
    return etag_response(request, payload)
