"""대시보드 집계 API — 현재가 기반 동적 손익 계산."""

import asyncio
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.encryption import decrypt
from app.core.redis_cache import get_redis_client
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.dashboard import AllocationItem, DashboardSummary, HoldingWithPnL, TriggeredAlert
from app.services.kis_price import (
    _cache_price,
    _get_cached_price,
    fetch_overseas_price_detail,
    fetch_usd_krw_rate,
)
from app.services.price_snapshot import fetch_domestic_price_detail
from app.models.alert import Alert
from app.api.alerts import check_triggered_alerts
from app.services.price_snapshot import get_prev_close
from app.core.ticker import is_domestic

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = get_logger(__name__)

_ZERO = Decimal("0")
# KIS 잔고 API ovrs_excg_cd (4자) → 가격 API EXCD (3자) 매핑
_MARKET_CODE_MAP = {
    "NASD": "NAS",
    "NYSE": "NYS",
    "AMEX": "AMS",
    "SEHK": "HKS",
    "TKSE": "TSE",
    "SHAA": "SHS",
    "SZAA": "SZS",
    "HASE": "HNX",
    "VNSE": "HSX",
}


def _normalize_market(code: str) -> str:
    """KIS 잔고 API 거래소 코드 → 가격 API EXCD 코드로 변환."""
    return _MARKET_CODE_MAP.get(code, code)


def _calc_pnl(
    quantity: Decimal, avg_price: Decimal, current_price: Optional[Decimal]
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    if current_price is None:
        return None, None
    invested = quantity * avg_price
    market_value = quantity * current_price
    pnl_amount = market_value - invested
    pnl_rate = (pnl_amount / invested * 100) if invested else None
    return pnl_amount, pnl_rate


@router.get("/summary", response_model=DashboardSummary)
@limiter.limit("120/minute")
async def get_summary(
    request: Request,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    # 사용자 포트폴리오 및 홀딩 조회
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolios = port_result.scalars().all()

    _empty = DashboardSummary(
        total_asset=_ZERO,
        total_invested=_ZERO,
        total_pnl_amount=_ZERO,
        total_pnl_rate=_ZERO,
        total_day_change_rate=None,
        day_change_pct=None,
        day_change_amount=None,
        holdings=[],
        allocation=[],
    )

    portfolio_ids = [p.id for p in portfolios]
    portfolio_name_map = {p.id: p.name for p in portfolios}
    if not portfolio_ids:
        return _empty

    hold_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids)).limit(500)
    )
    holdings = hold_result.scalars().all()

    if not holdings:
        return _empty

    # Ticker 분류: 국내(6자리 숫자) vs 해외
    tickers = list({h.ticker for h in holdings})
    domestic_tickers = [t for t in tickers if is_domestic(t)]
    overseas_tickers = [t for t in tickers if not is_domestic(t)]

    # 해외주식 ticker → market 코드 매핑 (Holding.market 에서)
    ticker_to_market: dict[str, str] = {}
    for h in holdings:
        if not is_domestic(h.ticker) and h.market:
            ticker_to_market[h.ticker] = _normalize_market(h.market)

    prices: dict[str, Optional[Decimal]] = {}

    # Force-refresh: clear price cache for these tickers
    if refresh and tickers:
        try:
            async with get_redis_client(settings.REDIS_URL) as r:
                keys = [f"price:{t}" for t in tickers]
                await r.delete(*keys)
        except Exception:
            pass

    acct_result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
    )
    kis_acct = acct_result.scalar_one_or_none()

    day_change_rates: dict[str, Optional[Decimal]] = {}
    w52_highs: dict[str, Optional[Decimal]] = {}
    w52_lows: dict[str, Optional[Decimal]] = {}
    exchange_rate: Decimal = Decimal("1450")  # default fallback
    kis_status: str = "ok"

    if kis_acct:
        try:
            app_key = decrypt(kis_acct.app_key_enc)
            app_secret = decrypt(kis_acct.app_secret_enc)

            async with httpx.AsyncClient(timeout=10.0) as client:
                # 환율 1회 조회 (해외주식이 있는 경우)
                if overseas_tickers:
                    exchange_rate = await fetch_usd_krw_rate(app_key, app_secret, client)

                # 국내주식: 현재가 + 전일 대비 + 52주 고/저
                domestic_tasks = [
                    fetch_domestic_price_detail(t, app_key, app_secret, client)
                    for t in domestic_tickers
                ]
                # 해외주식: 현재가 (USD) + 전일 대비
                overseas_tasks = [
                    fetch_overseas_price_detail(
                        t,
                        ticker_to_market.get(t, "NAS"),  # 기본값 NAS
                        app_key,
                        app_secret,
                        client,
                    )
                    for t in overseas_tickers
                ]

                all_results = await asyncio.gather(
                    *domestic_tasks,
                    *overseas_tasks,
                    return_exceptions=True,
                )

            fetched_count = 0
            # 국내주식 결과 처리
            for ticker, detail in zip(domestic_tickers, all_results[: len(domestic_tickers)]):
                if detail and not isinstance(detail, Exception):
                    prices[ticker] = detail.current
                    day_change_rates[ticker] = detail.day_change_rate
                    w52_highs[ticker] = detail.w52_high
                    w52_lows[ticker] = detail.w52_low
                    await _cache_price(ticker, detail.current)
                    fetched_count += 1
                else:
                    cached = await _get_cached_price(ticker)
                    if cached is not None:
                        prices[ticker] = cached
                        logger.info("Using cached price for %s: %s", ticker, cached)

            # 해외주식 결과 처리
            overseas_results = all_results[len(domestic_tickers):]
            for ticker, detail in zip(overseas_tickers, overseas_results):
                if detail and not isinstance(detail, Exception):
                    prices[ticker] = detail.current
                    day_change_rates[ticker] = detail.day_change_rate
                    w52_highs[ticker] = detail.w52_high
                    w52_lows[ticker] = detail.w52_low
                    await _cache_price(ticker, detail.current)
                    fetched_count += 1
                else:
                    cached = await _get_cached_price(ticker)
                    if cached is not None:
                        prices[ticker] = cached
                        logger.info("Using cached price for %s: %s", ticker, cached)

            # 조회 성공 종목이 하나도 없으면 degraded
            if tickers and fetched_count == 0:
                kis_status = "degraded"
                logger.warning("All price fetches failed — returning degraded dashboard")

        except Exception as e:
            kis_status = "degraded"
            logger.warning("Failed to fetch prices from KIS API: %s", e)

    # 수익 계산
    holding_items: list[HoldingWithPnL] = []
    total_asset = _ZERO
    total_invested = _ZERO

    for h in holdings:
        is_overseas = not is_domestic(h.ticker)
        current_price = prices.get(h.ticker)

        if is_overseas:
            # 해외주식: 현재가는 USD, 원화 환산으로 손익 계산
            invested_usd = h.quantity * h.avg_price
            invested_krw = invested_usd * exchange_rate

            if current_price is not None:
                market_value_usd = h.quantity * current_price
                market_value_krw = market_value_usd * exchange_rate
                pnl_amount_krw = market_value_krw - invested_krw
                pnl_rate = (pnl_amount_krw / invested_krw * 100) if invested_krw else None
                market_value = market_value_usd  # USD 평가금액 (수량 × 현재가)
            else:
                market_value_usd = invested_usd
                market_value_krw = invested_krw  # 현재가 없을 때 매입금액으로 대체
                pnl_amount_krw = None
                pnl_rate = None
                market_value = None

            total_invested += invested_krw
            total_asset += market_value_krw

            holding_items.append(
                HoldingWithPnL(
                    id=h.id,
                    ticker=h.ticker,
                    name=h.name,
                    portfolio_name=portfolio_name_map.get(h.portfolio_id),
                    quantity=h.quantity,
                    avg_price=h.avg_price,
                    current_price=current_price,
                    market_value=market_value,
                    market_value_krw=market_value_krw,  # 항상 원화 금액 반환 (정렬/합계용)
                    pnl_amount=pnl_amount_krw,
                    pnl_rate=pnl_rate,
                    day_change_rate=day_change_rates.get(h.ticker),
                    w52_high=w52_highs.get(h.ticker),
                    w52_low=w52_lows.get(h.ticker),
                    currency="USD",
                )
            )
        else:
            # 국내주식: 원화 기준
            pnl_amount, pnl_rate = _calc_pnl(h.quantity, h.avg_price, current_price)
            market_value = h.quantity * current_price if current_price is not None else None

            total_invested += h.quantity * h.avg_price
            total_asset += (
                market_value if market_value is not None else h.quantity * h.avg_price
            )

            holding_items.append(
                HoldingWithPnL(
                    id=h.id,
                    ticker=h.ticker,
                    name=h.name,
                    portfolio_name=portfolio_name_map.get(h.portfolio_id),
                    quantity=h.quantity,
                    avg_price=h.avg_price,
                    current_price=current_price,
                    market_value=market_value,
                    market_value_krw=market_value,
                    pnl_amount=pnl_amount,
                    pnl_rate=pnl_rate,
                    day_change_rate=day_change_rates.get(h.ticker),
                    w52_high=w52_highs.get(h.ticker),
                    w52_low=w52_lows.get(h.ticker),
                    currency="KRW",
                )
            )

    total_pnl_amount = total_asset - total_invested
    total_pnl_rate = (
        (total_pnl_amount / total_invested * 100) if total_invested else _ZERO
    )

    # 자산 배분 계산 (원화 환산 기준)
    allocation: list[AllocationItem] = []
    if total_asset > _ZERO:
        for item in holding_items:
            # allocation value는 항상 원화 기준
            value_krw = (
                item.market_value_krw
                if item.market_value_krw is not None
                else (
                    item.quantity * item.avg_price * exchange_rate
                    if item.currency == "USD"
                    else item.quantity * item.avg_price
                )
            )
            ratio = value_krw / total_asset * 100
            allocation.append(
                AllocationItem(
                    ticker=item.ticker, name=item.name, value=value_krw, ratio=ratio,
                )
            )
    allocation.sort(key=lambda x: x.ratio, reverse=True)

    # 포트폴리오 전일 대비: 시가총액 가중 평균
    total_day_change_rate: Optional[Decimal] = None
    weighted_sum = _ZERO
    weight_total = _ZERO
    for item in holding_items:
        if item.day_change_rate is not None:
            # 가중치는 원화 기준 시가총액
            weight = (
                item.market_value_krw
                if item.market_value_krw is not None
                else None
            )
            if weight is not None:
                weighted_sum += item.day_change_rate * weight
                weight_total += weight
    if weight_total > _ZERO:
        total_day_change_rate = weighted_sum / weight_total

    # price_snapshots 기반 전일 대비 계산
    day_change_pct: Optional[Decimal] = None
    day_change_amount: Optional[Decimal] = None
    prev_closes = await get_prev_close(db, tickers)
    if prev_closes and total_asset > _ZERO:
        prev_total = _ZERO
        curr_total = _ZERO
        for item in holding_items:
            prev_close = prev_closes.get(item.ticker)
            if prev_close is not None and prev_close > _ZERO:
                if item.currency == "USD":
                    prev_total += item.quantity * prev_close * exchange_rate
                    curr_total += (
                        item.market_value_krw
                        if item.market_value_krw is not None
                        else item.quantity * item.avg_price * exchange_rate
                    )
                else:
                    prev_total += item.quantity * prev_close
                    curr_total += (
                        item.market_value
                        if item.market_value is not None
                        else item.quantity * item.avg_price
                    )
        if prev_total > _ZERO:
            day_change_amount = curr_total - prev_total
            day_change_pct = day_change_amount / prev_total * 100

    # 목표가 알림 확인
    alert_result = await db.execute(
        select(Alert).where(Alert.user_id == current_user.id, Alert.is_active.is_(True))
    )
    active_alerts = list(alert_result.scalars().all())
    triggered_raw = check_triggered_alerts(active_alerts, prices)
    triggered_alerts = [TriggeredAlert(**a) for a in triggered_raw]

    return DashboardSummary(
        total_asset=total_asset,
        total_invested=total_invested,
        total_pnl_amount=total_pnl_amount,
        total_pnl_rate=total_pnl_rate,
        total_day_change_rate=total_day_change_rate,
        day_change_pct=day_change_pct,
        day_change_amount=day_change_amount,
        holdings=holding_items,
        allocation=allocation,
        triggered_alerts=triggered_alerts,
        usd_krw_rate=exchange_rate if overseas_tickers else None,
        kis_status=kis_status,
    )
