"""투자 성과 지표 API."""

import asyncio
import logging
import math
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.core.encryption import decrypt
from app.services.kis_price import _cache_price, _get_cached_price
from app.services.price_snapshot import fetch_domestic_price_detail
from app.data.sector_map import get_sector
from app.schemas.analytics import MonthlyReturn, PortfolioHistoryPoint, SectorAllocation

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)

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

    # 날짜별 포트폴리오 총 가치
    holding_map = {h.ticker: h for h in holdings}
    portfolio_values: list[float] = []
    for date_str in sorted(date_ticker_map.keys()):
        prices_on_date = date_ticker_map[date_str]
        value = sum(
            float(holding_map[t].quantity) * prices_on_date[t]
            for t in tickers
            if t in prices_on_date and t in holding_map
        )
        if value > 0:
            portfolio_values.append(value)

    # 일별 수익률
    daily_returns: list[float] = []
    for i in range(1, len(portfolio_values)):
        prev = portfolio_values[i - 1]
        if prev > 0:
            daily_returns.append((portfolio_values[i] - prev) / prev)

    # CAGR: 첫 스냅샷 ~ 현재
    cagr: Optional[float] = None
    if portfolio_values:
        years = len(portfolio_values) / 252
        cagr = _calc_cagr(portfolio_values[0], total_current, years)

    mdd = _calc_mdd(portfolio_values + [total_current]) if portfolio_values else 0.0
    sharpe = _calc_sharpe(daily_returns)

    return {
        "total_return_rate": round(total_return_rate, 2),
        "cagr": round(cagr, 2) if cagr is not None else None,
        "mdd": round(mdd, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
    }


@router.get("/monthly-returns", response_model=list[MonthlyReturn])
async def get_monthly_returns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MonthlyReturn]:
    """월별 포트폴리오 수익률 계산.

    price_snapshots에서 각 월의 마지막 거래일 종가를 취합하여
    전월 대비 수익률을 반환한다.
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

    return monthly_returns


@router.get("/portfolio-history", response_model=list[PortfolioHistoryPoint])
async def get_portfolio_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PortfolioHistoryPoint]:
    """일별 포트폴리오 총 평가금액 시계열 반환.

    price_snapshots에서 보유 종목의 날짜별 종가를 집계하여
    일별 포트폴리오 가치를 계산한다.
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

    sector_values: dict[str, float] = {}
    for h in holdings:
        sector = get_sector(h.ticker)
        value = float(h.quantity) * float(h.avg_price)
        sector_values[sector] = sector_values.get(sector, 0.0) + value

    total = sum(sector_values.values())
    if total <= 0:
        return []

    return [
        SectorAllocation(
            sector=sector,
            value=round(value, 0),
            weight=round(value / total * 100, 1),
        )
        for sector, value in sorted(sector_values.items(), key=lambda x: x[1], reverse=True)
    ]
