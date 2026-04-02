"""투자 성과 지표 API."""

import asyncio
import json
import math
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.redis_cache import RedisCache
from app.core.config import settings
from app.db.session import get_db
from app.models.fx_rate_snapshot import FxRateSnapshot
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.services.kis_price import _cache_price, _get_cached_price, get_cached_fx_rate
from app.core.ticker import is_domestic
from app.services.price_snapshot import fetch_domestic_price_detail
from app.data.sector_map import get_sector
from app.schemas.analytics import MonthlyReturn, PortfolioHistoryPoint, SectorAllocation

_analytics_cache = RedisCache(settings.REDIS_URL)
_ANALYTICS_CACHE_TTL = 3600  # 1시간; sync 시 무효화


HistoryPeriod = Literal["1W", "1M", "3M", "6M", "1Y", "ALL"]


def _period_cutoff(period: str) -> Optional[date_type]:
    """Return the earliest date for the given period, or None for ALL."""
    today = date_type.today()
    if period == "1W":
        return today - timedelta(days=7)
    if period == "1M":
        return today - timedelta(days=30)
    if period == "3M":
        return today - timedelta(days=91)
    if period == "6M":
        return today - timedelta(days=182)
    if period == "1Y":
        return today - timedelta(days=365)
    return None  # ALL


def _analytics_key(user_id: int, endpoint: str) -> str:
    return f"analytics:{user_id}:{endpoint}"


async def invalidate_analytics_cache(user_id: int) -> None:
    """sync 성공 후 호출 — 해당 유저의 분석 캐시 전체 삭제."""
    for endpoint in ("metrics", "monthly-returns", "sector-allocation", "fx-gain-loss"):
        await _analytics_cache.delete(_analytics_key(user_id, endpoint))
    # period-specific keys for portfolio-history and krw-asset-history
    for period in ("1W", "1M", "3M", "6M", "1Y", "ALL"):
        await _analytics_cache.delete(_analytics_key(user_id, f"portfolio-history:{period}"))
    for period in ("1M", "3M", "6M", "1Y", "ALL"):
        await _analytics_cache.delete(_analytics_key(user_id, f"krw-asset-history:{period}"))


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


@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """포트폴리오 성과 지표 계산.

    Returns: total_return_rate, cagr, mdd, sharpe_ratio
    """
    cache_key = _analytics_key(current_user.id, "metrics")
    cached = await _analytics_cache.get(cache_key)
    if cached:
        return json.loads(cached)

    # 보유 종목 조회
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    if not portfolio_ids:
        return {"total_return_rate": None, "cagr": None, "mdd": None, "sharpe_ratio": None}

    hold_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    holdings = hold_result.scalars().all()
    if not holdings:
        return {"total_return_rate": None, "cagr": None, "mdd": None, "sharpe_ratio": None}

    tickers = list({h.ticker for h in holdings})

    # 현재가 조회
    acct_result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
    )
    acct = acct_result.scalar_one_or_none()
    current_prices: dict[str, Optional[Decimal]] = {}
    if acct:
        try:
            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)
            async with httpx.AsyncClient(timeout=10.0) as client:
                details = await asyncio.gather(
                    *[fetch_domestic_price_detail(t, app_key, app_secret, client) for t in tickers],
                    return_exceptions=True,
                )
            for ticker, detail in zip(tickers, details):
                if detail and not isinstance(detail, Exception):
                    current_prices[ticker] = detail.current
                    await _cache_price(ticker, detail.current)
                else:
                    cached = await _get_cached_price(ticker)
                    if cached is not None:
                        current_prices[ticker] = cached
        except Exception as e:
            logger.warning("Failed to fetch prices for metrics: %s", e)

    # 현재 포트폴리오 가치 계산
    total_invested = sum(float(h.quantity) * float(h.avg_price) for h in holdings)
    total_current = sum(
        float(h.quantity) * float(current_prices.get(h.ticker) or h.avg_price)
        for h in holdings
    )

    if total_invested <= 0:
        return {"total_return_rate": None, "cagr": None, "mdd": None, "sharpe_ratio": None}

    total_return_rate = (total_current - total_invested) / total_invested * 100

    # price_snapshots 기반 일별 포트폴리오 가치 시계열 계산
    snap_result = await db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker.in_(tickers))
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

    # 날짜별 포트폴리오 총 가치 (날짜 추적 포함)
    holding_map = {h.ticker: h for h in holdings}
    portfolio_date_values: list[tuple[str, float]] = []
    for date_str in sorted(date_ticker_map.keys()):
        prices_on_date = date_ticker_map[date_str]
        value = sum(
            float(holding_map[t].quantity) * prices_on_date[t]
            for t in tickers
            if t in prices_on_date and t in holding_map
        )
        if value > 0:
            portfolio_date_values.append((date_str, value))

    portfolio_values = [v for _, v in portfolio_date_values]

    # 일별 수익률
    daily_returns: list[float] = []
    for i in range(1, len(portfolio_values)):
        prev = portfolio_values[i - 1]
        if prev > 0:
            daily_returns.append((portfolio_values[i] - prev) / prev)

    # CAGR: 실제 날짜 범위 기반 (최소 30일 이상 데이터 필요)
    cagr: Optional[float] = None
    if portfolio_date_values:
        start_date = date_type.fromisoformat(portfolio_date_values[0][0])
        end_date = date_type.fromisoformat(portfolio_date_values[-1][0])
        days = (end_date - start_date).days
        if days >= 30:
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
    await _analytics_cache.setex(cache_key, _ANALYTICS_CACHE_TTL, json.dumps(result))
    return result


@router.get("/monthly-returns", response_model=list[MonthlyReturn])
async def get_monthly_returns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MonthlyReturn]:
    """월별 포트폴리오 수익률 계산.

    price_snapshots에서 각 월의 마지막 거래일 종가를 취합하여
    전월 대비 수익률을 반환한다.
    """
    cache_key = _analytics_key(current_user.id, "monthly-returns")
    cached = await _analytics_cache.get(cache_key)
    if cached:
        return [MonthlyReturn(**item) for item in json.loads(cached)]

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
    holding_map = {h.ticker: h for h in holdings}

    snap_result = await db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker.in_(tickers))
        .order_by(PriceSnapshot.snapshot_date)
    )
    snapshots = snap_result.scalars().all()
    if not snapshots:
        return []

    # 날짜별 {ticker: close} 맵 구축
    date_ticker_map: dict[str, dict[str, float]] = {}
    for snap in snapshots:
        d = snap.snapshot_date.isoformat()
        if d not in date_ticker_map:
            date_ticker_map[d] = {}
        date_ticker_map[d][snap.ticker] = float(snap.close)

    # 월별 마지막 날짜의 포트폴리오 가치 계산
    month_end_values: dict[str, float] = {}  # key: "YYYY-MM"
    for date_str in sorted(date_ticker_map.keys()):
        prices_on_date = date_ticker_map[date_str]
        value = sum(
            float(holding_map[t].quantity) * prices_on_date[t]
            for t in tickers
            if t in prices_on_date and t in holding_map
        )
        if value > 0:
            month_key = date_str[:7]  # "YYYY-MM"
            month_end_values[month_key] = value  # 월 내 마지막 날로 덮어쓰기

    if len(month_end_values) < 2:
        return []

    # 월별 수익률 계산
    sorted_months = sorted(month_end_values.keys())
    monthly_returns: list[MonthlyReturn] = []
    for i in range(1, len(sorted_months)):
        prev_key = sorted_months[i - 1]
        curr_key = sorted_months[i]
        prev_value = month_end_values[prev_key]
        curr_value = month_end_values[curr_key]
        if prev_value > 0:
            return_rate = (curr_value - prev_value) / prev_value * 100
            year, month = int(curr_key[:4]), int(curr_key[5:7])
            monthly_returns.append(
                MonthlyReturn(year=year, month=month, return_rate=round(return_rate, 2))
            )

    await _analytics_cache.setex(
        cache_key, _ANALYTICS_CACHE_TTL,
        json.dumps([r.model_dump() for r in monthly_returns])
    )
    return monthly_returns


@router.get("/portfolio-history", response_model=list[PortfolioHistoryPoint])
async def get_portfolio_history(
    period: str = Query(default="ALL", description="기간 필터: 1M, 3M, 6M, 1Y, ALL"),
    portfolio_id: Optional[int] = Query(default=None, description="특정 포트폴리오 ID (미지정 시 전체 합산)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PortfolioHistoryPoint]:
    """일별 포트폴리오 총 평가금액 시계열 반환.

    price_snapshots에서 보유 종목의 날짜별 종가를 집계하여
    일별 포트폴리오 가치를 계산한다.
    period 파라미터로 반환 기간 필터링 가능 (1W/1M/3M/6M/1Y/ALL).
    portfolio_id 파라미터로 특정 포트폴리오만 조회 가능.
    """
    normalized_period = period.upper() if period.upper() in ("1W", "1M", "3M", "6M", "1Y") else "ALL"
    cache_suffix = f"portfolio-history:{normalized_period}" + (f":{portfolio_id}" if portfolio_id else "")
    cache_key = _analytics_key(current_user.id, cache_suffix)
    cached = await _analytics_cache.get(cache_key)
    if cached:
        return [PortfolioHistoryPoint(**item) for item in json.loads(cached)]

    port_query = select(Portfolio).where(Portfolio.user_id == current_user.id)
    if portfolio_id is not None:
        port_query = port_query.where(Portfolio.id == portfolio_id)
    port_result = await db.execute(port_query)
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
    holding_map = {h.ticker: h for h in holdings}

    cutoff = _period_cutoff(normalized_period)
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

    # 날짜별 {ticker: close}
    date_ticker_map: dict[str, dict[str, float]] = {}
    for snap in snapshots:
        d = snap.snapshot_date.isoformat()
        if d not in date_ticker_map:
            date_ticker_map[d] = {}
        date_ticker_map[d][snap.ticker] = float(snap.close)

    history: list[PortfolioHistoryPoint] = []
    for date_str in sorted(date_ticker_map.keys()):
        prices_on_date = date_ticker_map[date_str]
        value = sum(
            float(holding_map[t].quantity) * prices_on_date[t]
            for t in tickers
            if t in prices_on_date and t in holding_map
        )
        if value > 0:
            history.append(PortfolioHistoryPoint(date=date_str, value=round(value, 0)))

    await _analytics_cache.setex(
        cache_key, _ANALYTICS_CACHE_TTL,
        json.dumps([h.model_dump() for h in history])
    )
    return history


@router.get("/sector-allocation", response_model=list[SectorAllocation])
async def get_sector_allocation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SectorAllocation]:
    """보유 종목의 섹터별 자산 배분 반환.

    평균 매입가 기준으로 섹터별 투자 금액 비중을 계산한다.
    현재가 조회 없이 빠르게 응답한다.
    """
    cache_key = _analytics_key(current_user.id, "sector-allocation")
    cached = await _analytics_cache.get(cache_key)
    if cached:
        return [SectorAllocation(**item) for item in json.loads(cached)]

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
        return []

    result = [
        SectorAllocation(
            sector=sector,
            value=round(value, 0),
            weight=round(value / total * 100, 1),
        )
        for sector, value in sorted(sector_values.items(), key=lambda x: x[1], reverse=True)
    ]
    await _analytics_cache.setex(
        cache_key, _ANALYTICS_CACHE_TTL,
        json.dumps([r.model_dump() for r in result])
    )
    return result


@router.get("/fx-gain-loss")
async def get_fx_gain_loss(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """해외주식 보유 종목별 환차익/환차손 분리 계산.

    각 해외주식에 대해 주가 수익(USD 기준)과 환차익(KRW 기준)을 분리하여 반환한다.
    - 주가 수익 = (현재가 - 매입가) × 수량 (USD)
    - 환차익 = 매입 원금 × (현재 환율 / 매입 시 환율 - 1) (KRW)

    매입 시 환율: 보유 종목 created_at 날짜에 가장 가까운 fx_rate_snapshots 환율 사용.
    현재가: Redis 캐시 우선, 없으면 avg_price fallback.
    현재 환율: Redis 캐시(get_cached_fx_rate) 사용.
    """
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    if not portfolio_ids:
        return []

    hold_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    all_holdings = hold_result.scalars().all()

    # 해외주식만 필터링 (ticker가 숫자 6자리가 아닌 경우)
    overseas = [h for h in all_holdings if not is_domestic(h.ticker)]
    if not overseas:
        return []

    # 현재 환율
    fx_current = await get_cached_fx_rate()

    # 날짜별 환율 스냅샷 조회 (최근 2년)
    cutoff_fx = date_type.today() - timedelta(days=730)
    fx_result = await db.execute(
        select(FxRateSnapshot)
        .where(
            FxRateSnapshot.currency_pair == "USDKRW",
            FxRateSnapshot.snapshot_date >= cutoff_fx,
        )
        .order_by(FxRateSnapshot.snapshot_date)
    )
    fx_snapshots = fx_result.scalars().all()
    # 날짜 -> 환율 맵
    fx_date_map: dict[str, float] = {
        snap.snapshot_date.isoformat(): float(snap.rate)
        for snap in fx_snapshots
    }
    fx_dates_sorted = sorted(fx_date_map.keys())

    def _nearest_fx_rate(target_date: str) -> float:
        """target_date에 가장 가까운 환율 반환."""
        if not fx_dates_sorted:
            return fx_current
        # 이분 탐색으로 가장 가까운 날짜 찾기
        import bisect
        idx = bisect.bisect_left(fx_dates_sorted, target_date)
        candidates: list[float] = []
        if idx < len(fx_dates_sorted):
            candidates.append(fx_date_map[fx_dates_sorted[idx]])
        if idx > 0:
            candidates.append(fx_date_map[fx_dates_sorted[idx - 1]])
        if not candidates:
            return fx_current
        # 날짜 차이 기준으로 가장 가까운 것 선택
        if len(candidates) == 1:
            return candidates[0]
        d0 = abs((date_type.fromisoformat(fx_dates_sorted[max(0, idx - 1)]) -
                  date_type.fromisoformat(target_date)).days)
        d1 = abs((date_type.fromisoformat(fx_dates_sorted[min(len(fx_dates_sorted) - 1, idx)]) -
                  date_type.fromisoformat(target_date)).days)
        return candidates[1] if d0 <= d1 else candidates[0]

    result_items: list[dict] = []
    for h in overseas:
        # 현재가 (USD)
        cached_price = await _get_cached_price(h.ticker)
        current_price_usd = float(cached_price) if cached_price is not None else float(h.avg_price)

        qty = float(h.quantity)
        avg_price_usd = float(h.avg_price)

        # 매입 시 환율 (보유 종목 created_at 날짜 기준)
        buy_date_str = h.created_at.date().isoformat()
        fx_at_buy = _nearest_fx_rate(buy_date_str)

        # 주가 수익 (USD)
        stock_pnl_usd = (current_price_usd - avg_price_usd) * qty
        # 주가 수익 (KRW, 현재 환율 기준)
        stock_gain_krw = stock_pnl_usd * fx_current

        # 환차익 (KRW): 매입 원금 KRW × (현재환율/매입환율 - 1)
        buy_value_usd = avg_price_usd * qty
        buy_value_krw = buy_value_usd * fx_at_buy
        fx_gain_krw = buy_value_usd * fx_current - buy_value_krw

        # 총 손익 (KRW)
        total_pnl_krw = stock_gain_krw + fx_gain_krw

        result_items.append({
            "ticker": h.ticker,
            "name": h.name,
            "quantity": qty,
            "avg_price_usd": round(avg_price_usd, 4),
            "current_price_usd": round(current_price_usd, 4),
            "stock_pnl_usd": round(stock_pnl_usd, 2),
            "fx_rate_at_buy": round(fx_at_buy, 2),
            "fx_rate_current": round(fx_current, 2),
            "fx_gain_krw": round(fx_gain_krw, 0),
            "stock_gain_krw": round(stock_gain_krw, 0),
            "total_pnl_krw": round(total_pnl_krw, 0),
        })

    return result_items


@router.get("/krw-asset-history")
async def get_krw_asset_history(
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
    normalized_period = period.upper() if period.upper() in ("1W", "1M", "3M", "6M", "1Y") else "ALL"
    cache_key = _analytics_key(current_user.id, f"krw-asset-history:{normalized_period}")
    cached = await _analytics_cache.get(cache_key)
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
    holding_map = {h.ticker: h for h in holdings}
    domestic_tickers = [t for t in tickers if is_domestic(t)]
    overseas_tickers = [t for t in tickers if not is_domestic(t)]

    cutoff = _period_cutoff(normalized_period)

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
    fx_date_map: dict[str, float] = {
        snap.snapshot_date.isoformat(): float(snap.rate)
        for snap in fx_snapshots
    }

    # forward-fill 환율: 날짜별 가장 최근 환율 채우기
    fallback_fx = await get_cached_fx_rate()
    filled_fx: dict[str, float] = {}
    last_known_fx: float = fallback_fx
    for d in all_dates:
        if d in fx_date_map:
            last_known_fx = fx_date_map[d]
        filled_fx[d] = last_known_fx

    # 날짜별 원화 환산 총 자산 계산
    history: list[dict] = []
    for date_str in all_dates:
        prices_on_date = date_ticker_map[date_str]
        fx_rate = filled_fx.get(date_str, fallback_fx)

        domestic_value = sum(
            float(holding_map[t].quantity) * prices_on_date[t]
            for t in domestic_tickers
            if t in prices_on_date and t in holding_map
        )
        overseas_value_usd = sum(
            float(holding_map[t].quantity) * prices_on_date[t]
            for t in overseas_tickers
            if t in prices_on_date and t in holding_map
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

    await _analytics_cache.setex(cache_key, _ANALYTICS_CACHE_TTL, json.dumps(history))
    return history


@router.get("/fx-history")
async def get_fx_history(
    currency_pair: str = Query(default="USDKRW", description="통화쌍 (예: USDKRW)"),
    days: int = Query(default=90, ge=1, le=365, description="조회 기간 (일, 최대 365)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """USD/KRW 환율 히스토리 반환.

    fx_rate_snapshots 테이블에서 최근 N일 환율 데이터를 조회한다.
    스케줄러가 매 평일 장 마감 후(KST 16:30) 저장한다.

    응답 예시:
    [
      {"date": "2026-03-28", "rate": 1380.5},
      {"date": "2026-03-27", "rate": 1375.0}
    ]
    """
    cutoff = date_type.today() - timedelta(days=days)
    result = await db.execute(
        select(FxRateSnapshot)
        .where(
            FxRateSnapshot.currency_pair == currency_pair,
            FxRateSnapshot.snapshot_date >= cutoff,
        )
        .order_by(FxRateSnapshot.snapshot_date)
    )
    snapshots = result.scalars().all()
    return [
        {"date": snap.snapshot_date.isoformat(), "rate": float(snap.rate)}
        for snap in snapshots
    ]
