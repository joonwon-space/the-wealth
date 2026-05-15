"""투자 히스토리 API — portfolio-history, krw-asset-history."""

import json
from datetime import date as date_type, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._etag import etag_response
from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.ticker import is_domestic
from app.db.session import get_db
from app.models.fx_rate_snapshot import FxRateSnapshot
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.schemas.analytics import PortfolioHistoryPoint
from app.services.analytics_utils import (
    ANALYTICS_CACHE_TTL,
    analytics_key,
    get_analytics_cache,
    period_cutoff,
)
from app.services.fx_utils import forward_fill_rates
from app.services.kis_price import get_cached_fx_rate

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)


@router.get("/portfolio-history", response_model=list[PortfolioHistoryPoint])
@limiter.limit("30/minute")
async def get_portfolio_history(
    request: Request,
    period: str = Query(default="ALL", description="기간 필터: 1M, 3M, 6M, 1Y, ALL"),
    portfolio_id: Optional[int] = Query(default=None, description="특정 포트폴리오 ID (미지정 시 전체 합산)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FastAPIResponse:
    """일별 포트폴리오 총 평가금액 시계열 반환 (ETag/304 적용).

    price_snapshots에서 보유 종목의 날짜별 종가를 집계하여
    일별 포트폴리오 가치를 계산한다.
    period 파라미터로 반환 기간 필터링 가능 (1W/1M/3M/6M/1Y/ALL).
    portfolio_id 파라미터로 특정 포트폴리오만 조회 가능.
    """
    _cache = get_analytics_cache()
    normalized_period = period.upper() if period.upper() in ("1W", "1M", "3M", "6M", "1Y") else "ALL"
    cache_suffix = f"portfolio-history:{normalized_period}" + (f":{portfolio_id}" if portfolio_id else "")
    cache_key = analytics_key(current_user.id, cache_suffix)
    cached = await _cache.get(cache_key)
    if cached:
        return etag_response(request, json.loads(cached))

    port_query = select(Portfolio).where(Portfolio.user_id == current_user.id)
    if portfolio_id is not None:
        port_query = port_query.where(Portfolio.id == portfolio_id)
    port_result = await db.execute(port_query)
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
    # 같은 ticker가 여러 portfolio에 분산되면 dict comprehension은 마지막
    # holding으로 덮어써 일부 보유분이 누락된다. ticker별 quantity를 합산한다.
    qty_map: dict[str, float] = {}
    for h in holdings:
        qty_map[h.ticker] = qty_map.get(h.ticker, 0.0) + float(h.quantity)

    cutoff = period_cutoff(normalized_period)
    snap_query = (
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker.in_(tickers))
        .order_by(PriceSnapshot.snapshot_date)
    )
    if cutoff is not None:
        snap_query = snap_query.where(PriceSnapshot.snapshot_date >= cutoff)

    snap_result = await db.execute(snap_query)
    snapshots = snap_result.scalars().all()
    if not snapshots:
        return etag_response(request, [])

    # 날짜별 {ticker: close}
    date_ticker_map: dict[str, dict[str, float]] = {}
    for snap in snapshots:
        d = snap.snapshot_date.isoformat()
        if d not in date_ticker_map:
            date_ticker_map[d] = {}
        date_ticker_map[d][snap.ticker] = float(snap.close)

    # forward-fill + backward-fill:
    # - forward-fill: 일부 ticker가 특정 날짜에 PriceSnapshot이 없으면 직전 값 유지.
    # - backward-fill: 첫 등장 이전 날짜는 그 ticker의 첫 close로 평가 (현재 보유
    #   종목을 기간 시작 시점에 가지고 있었다고 가정한 시계열). 이렇게 하면 일부
    #   ticker가 기간 중간에야 PriceSnapshot이 생기는 경우에도 history 차트가
    #   끊기지 않고 시작값이 안정된다.
    sorted_dates = sorted(date_ticker_map.keys())
    first_close: dict[str, float] = {}
    for snap in snapshots:
        if snap.ticker not in first_close:
            first_close[snap.ticker] = float(snap.close)

    last_close: dict[str, float] = {}
    history: list[PortfolioHistoryPoint] = []
    for date_str in sorted_dates:
        for t, close in date_ticker_map[date_str].items():
            last_close[t] = close
        # forward-fill 우선, 없으면 backward-fill (첫 close)
        effective = {**first_close, **last_close}
        value = sum(qty_map[t] * effective[t] for t in tickers if t in effective)
        if value > 0:
            history.append(PortfolioHistoryPoint(date=date_str, value=round(value, 0)))

    payload = [h.model_dump() for h in history]
    await _cache.setex(cache_key, ANALYTICS_CACHE_TTL, json.dumps(payload))
    return etag_response(request, payload)


@router.get("/krw-asset-history")
@limiter.limit("30/minute")
async def get_krw_asset_history(
    request: Request,
    period: str = Query(default="ALL", description="기간 필터: 1M, 3M, 6M, 1Y, ALL"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """환율 변동 반영 원화 환산 총 자산 추이.

    price_snapshots와 fx_rate_snapshots를 결합하여 날짜별로
    국내주식(KRW)과 해외주식(USD→KRW 환산)을 합산한 총 자산 추이를 반환한다.

    해당 날짜의 fx_rate_snapshots 환율을 사용하며,
    없으면 가장 최근 이전 날짜의 환율을 forward-fill한다.

    응답 예시:
    [
      {"date": "2026-03-28", "value": 15000000, "domestic_value": 10000000, "overseas_value_krw": 5000000},
      ...
    ]
    """
    _cache = get_analytics_cache()
    normalized_period = period.upper() if period.upper() in ("1W", "1M", "3M", "6M", "1Y") else "ALL"
    cache_key = analytics_key(current_user.id, f"krw-asset-history:{normalized_period}")
    cached = await _cache.get(cache_key)
    if cached:
        return json.loads(cached)

    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    if not portfolio_ids:
        return []

    hold_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    holdings = hold_result.scalars().all()
    if not holdings:
        return []

    tickers = list({h.ticker for h in holdings})
    # 같은 ticker가 여러 portfolio에 분산되면 quantity를 합산해야 한다.
    qty_map: dict[str, float] = {}
    for h in holdings:
        qty_map[h.ticker] = qty_map.get(h.ticker, 0.0) + float(h.quantity)
    domestic_tickers = [t for t in tickers if is_domestic(t)]
    overseas_tickers = [t for t in tickers if not is_domestic(t)]

    cutoff = period_cutoff(normalized_period)

    # 종가 스냅샷 조회
    snap_query = (
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker.in_(tickers))
        .order_by(PriceSnapshot.snapshot_date)
    )
    if cutoff is not None:
        snap_query = snap_query.where(PriceSnapshot.snapshot_date >= cutoff)
    snap_result = await db.execute(snap_query)
    snapshots = snap_result.scalars().all()
    if not snapshots:
        return []

    # 날짜별 {ticker: close} 맵
    date_ticker_map: dict[str, dict[str, float]] = {}
    for snap in snapshots:
        d = snap.snapshot_date.isoformat()
        if d not in date_ticker_map:
            date_ticker_map[d] = {}
        date_ticker_map[d][snap.ticker] = float(snap.close)

    all_dates = sorted(date_ticker_map.keys())

    # 환율 스냅샷 조회 (기간 기준)
    fx_cutoff = cutoff if cutoff is not None else (date_type.today() - timedelta(days=1825))
    fx_result = await db.execute(
        select(FxRateSnapshot)
        .where(
            FxRateSnapshot.currency_pair == "USDKRW",
            FxRateSnapshot.snapshot_date >= fx_cutoff,
        )
        .order_by(FxRateSnapshot.snapshot_date)
    )
    fx_snapshots = fx_result.scalars().all()

    # forward-fill 환율: 날짜별 가장 최근 환율 채우기
    fallback_fx = await get_cached_fx_rate()
    filled_fx = forward_fill_rates(fx_snapshots, all_dates, fallback_fx)

    # forward-fill + backward-fill (첫 close로 그 이전 날짜 채움)
    first_close: dict[str, float] = {}
    for snap in snapshots:
        if snap.ticker not in first_close:
            first_close[snap.ticker] = float(snap.close)

    last_close: dict[str, float] = {}
    history: list[dict] = []
    for date_str in all_dates:
        for t, close in date_ticker_map[date_str].items():
            last_close[t] = close
        effective = {**first_close, **last_close}
        fx_rate = filled_fx.get(date_str, fallback_fx)

        domestic_value = sum(
            qty_map[t] * effective[t]
            for t in domestic_tickers
            if t in effective
        )
        overseas_value_usd = sum(
            qty_map[t] * effective[t]
            for t in overseas_tickers
            if t in effective
        )
        overseas_value_krw = overseas_value_usd * fx_rate
        total_value = domestic_value + overseas_value_krw

        if total_value > 0:
            history.append({
                "date": date_str,
                "value": round(total_value, 0),
                "domestic_value": round(domestic_value, 0),
                "overseas_value_krw": round(overseas_value_krw, 0),
            })

    await _cache.setex(cache_key, ANALYTICS_CACHE_TTL, json.dumps(history))
    return history
