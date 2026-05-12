"""대시보드 집계 API — 현재가 기반 동적 손익 계산."""

import asyncio
import hashlib
import json
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response as FastAPIResponse
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
from app.schemas.dashboard import AllocationItem, DashboardSummary, DashboardSummaryResponse, HoldingWithPnL, TriggeredAlert
from app.services.kis_price import (
    _cache_price,
    _get_cached_price,
    fetch_overseas_price_detail,
    fetch_usd_krw_rate,
)
from app.services.price_snapshot import fetch_domestic_price_detail
from app.models.alert import Alert
from app.api.alerts import check_triggered_alerts
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


class _PriceFetchResult:
    """_fetch_prices 반환값."""
    __slots__ = ("prices", "prev_closes", "day_change_rates", "w52_highs", "w52_lows", "exchange_rate", "kis_status")

    def __init__(
        self,
        prices: dict[str, Optional[Decimal]],
        prev_closes: dict[str, Optional[Decimal]],
        day_change_rates: dict[str, Optional[Decimal]],
        w52_highs: dict[str, Optional[Decimal]],
        w52_lows: dict[str, Optional[Decimal]],
        exchange_rate: Decimal,
        kis_status: str,
    ) -> None:
        self.prices = prices
        self.prev_closes = prev_closes
        self.day_change_rates = day_change_rates
        self.w52_highs = w52_highs
        self.w52_lows = w52_lows
        self.exchange_rate = exchange_rate
        self.kis_status = kis_status


async def _fetch_prices(
    holdings: list[Holding],
    kis_acct: Optional[KisAccount],
    refresh: bool,
) -> _PriceFetchResult:
    """KIS API에서 보유 종목 현재가를 병렬 조회한다."""
    tickers = list({h.ticker for h in holdings})
    domestic_tickers = [t for t in tickers if is_domestic(t)]
    overseas_tickers = [t for t in tickers if not is_domestic(t)]

    ticker_to_market: dict[str, str] = {}
    for h in holdings:
        if not is_domestic(h.ticker) and h.market:
            ticker_to_market[h.ticker] = _normalize_market(h.market)

    prices: dict[str, Optional[Decimal]] = {}
    prev_closes: dict[str, Optional[Decimal]] = {}
    day_change_rates: dict[str, Optional[Decimal]] = {}
    w52_highs: dict[str, Optional[Decimal]] = {}
    w52_lows: dict[str, Optional[Decimal]] = {}
    exchange_rate: Decimal = Decimal("1450")
    kis_status = "ok"

    if refresh and tickers:
        try:
            async with get_redis_client(settings.REDIS_URL) as r:
                keys = [f"price:{t}" for t in tickers]
                await r.delete(*keys)
        except Exception:
            pass

    if kis_acct:
        try:
            app_key = decrypt(kis_acct.app_key_enc)
            app_secret = decrypt(kis_acct.app_secret_enc)

            # 전체 KIS 조회에 20초 글로벌 타임아웃 — degraded 시 배치 누적으로
            # Cloudflare 30초 제한 초과하는 것을 방지한다.
            async with asyncio.timeout(20):
                async with httpx.AsyncClient(timeout=10.0) as client:
                    if overseas_tickers:
                        exchange_rate = await fetch_usd_krw_rate(app_key, app_secret, client)

                    domestic_tasks = [
                        fetch_domestic_price_detail(t, app_key, app_secret, client)
                        for t in domestic_tickers
                    ]
                    overseas_tasks = [
                        fetch_overseas_price_detail(t, ticker_to_market.get(t, "NAS"), app_key, app_secret, client)
                        for t in overseas_tickers
                    ]
                    all_results = await asyncio.gather(*domestic_tasks, *overseas_tasks, return_exceptions=True)

            fetched_count = 0
            for ticker, detail in zip(domestic_tickers, all_results[: len(domestic_tickers)]):
                if detail and not isinstance(detail, Exception):
                    prices[ticker] = detail.current
                    if detail.prev_close and detail.prev_close > _ZERO:
                        prev_closes[ticker] = detail.prev_close
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

            for ticker, detail in zip(overseas_tickers, all_results[len(domestic_tickers):]):
                if detail and not isinstance(detail, Exception):
                    prices[ticker] = detail.current
                    if detail.prev_close and detail.prev_close > _ZERO:
                        prev_closes[ticker] = detail.prev_close
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

            if tickers and fetched_count == 0:
                kis_status = "degraded"
                logger.warning("All price fetches failed — returning degraded dashboard")

        except Exception as e:
            kis_status = "degraded"
            logger.warning("Failed to fetch prices from KIS API: %s", e)

    return _PriceFetchResult(prices, prev_closes, day_change_rates, w52_highs, w52_lows, exchange_rate, kis_status)


def _aggregate_holdings(
    holdings: list[Holding],
    portfolio_name_map: dict[int, str],
    price_result: _PriceFetchResult,
) -> tuple[list[HoldingWithPnL], Decimal, Decimal]:
    """보유 종목별 손익을 집계해 HoldingWithPnL 목록과 총 자산/투자금을 반환한다."""
    prices = price_result.prices
    day_change_rates = price_result.day_change_rates
    w52_highs = price_result.w52_highs
    w52_lows = price_result.w52_lows
    exchange_rate = price_result.exchange_rate

    holding_items: list[HoldingWithPnL] = []
    total_asset = _ZERO
    total_invested = _ZERO

    for h in holdings:
        current_price = prices.get(h.ticker)
        if not is_domestic(h.ticker):
            invested_usd = h.quantity * h.avg_price
            invested_krw = invested_usd * exchange_rate
            if current_price is not None:
                market_value_usd = h.quantity * current_price
                market_value_krw = market_value_usd * exchange_rate
                pnl_amount_krw = market_value_krw - invested_krw
                pnl_rate = (pnl_amount_krw / invested_krw * 100) if invested_krw else None
                market_value = market_value_usd
            else:
                market_value_usd = invested_usd
                market_value_krw = invested_krw
                pnl_amount_krw = None
                pnl_rate = None
                market_value = None
            total_invested += invested_krw
            total_asset += market_value_krw
            holding_items.append(HoldingWithPnL(
                id=h.id, ticker=h.ticker, name=h.name,
                portfolio_name=portfolio_name_map.get(h.portfolio_id),
                quantity=h.quantity, avg_price=h.avg_price,
                current_price=current_price, market_value=market_value,
                market_value_krw=market_value_krw, pnl_amount=pnl_amount_krw,
                pnl_rate=pnl_rate, day_change_rate=day_change_rates.get(h.ticker),
                w52_high=w52_highs.get(h.ticker), w52_low=w52_lows.get(h.ticker),
                currency="USD",
            ))
        else:
            pnl_amount, pnl_rate = _calc_pnl(h.quantity, h.avg_price, current_price)
            market_value = h.quantity * current_price if current_price is not None else None
            total_invested += h.quantity * h.avg_price
            total_asset += market_value if market_value is not None else h.quantity * h.avg_price
            holding_items.append(HoldingWithPnL(
                id=h.id, ticker=h.ticker, name=h.name,
                portfolio_name=portfolio_name_map.get(h.portfolio_id),
                quantity=h.quantity, avg_price=h.avg_price,
                current_price=current_price, market_value=market_value,
                market_value_krw=market_value, pnl_amount=pnl_amount,
                pnl_rate=pnl_rate, day_change_rate=day_change_rates.get(h.ticker),
                w52_high=w52_highs.get(h.ticker), w52_low=w52_lows.get(h.ticker),
                currency="KRW",
            ))

    return holding_items, total_asset, total_invested


def _build_allocation(
    holding_items: list[HoldingWithPnL],
    total_asset: Decimal,
    exchange_rate: Decimal,
) -> list[AllocationItem]:
    """보유 종목 목록에서 자산 배분 비율을 계산한다."""
    allocation: list[AllocationItem] = []
    if total_asset <= _ZERO:
        return allocation
    for item in holding_items:
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
        allocation.append(AllocationItem(ticker=item.ticker, name=item.name, value=value_krw, ratio=ratio))
    allocation.sort(key=lambda x: x.ratio, reverse=True)
    return allocation


@router.get("/summary", response_model=DashboardSummaryResponse)
@limiter.limit("120/minute")
async def get_summary(
    request: Request,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary | FastAPIResponse:
    port_result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolios = port_result.scalars().all()

    _empty = DashboardSummary(
        total_asset=_ZERO, total_invested=_ZERO, total_pnl_amount=_ZERO,
        total_pnl_rate=_ZERO, total_day_change_rate=None,
        day_change_pct=None, day_change_amount=None, holdings=[], allocation=[],
    )

    portfolio_ids = [p.id for p in portfolios]
    portfolio_name_map = {p.id: p.name for p in portfolios}
    if not portfolio_ids:
        return _empty

    hold_result, acct_result = await asyncio.gather(
        db.execute(select(Holding).where(Holding.portfolio_id.in_(portfolio_ids)).limit(500)),
        db.execute(select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)),
    )
    holdings = hold_result.scalars().all()
    if not holdings:
        return _empty

    kis_acct = acct_result.scalar_one_or_none()

    price_result = await _fetch_prices(list(holdings), kis_acct, refresh)
    holding_items, total_asset, total_invested = _aggregate_holdings(
        list(holdings), portfolio_name_map, price_result
    )

    total_pnl_amount = total_asset - total_invested
    total_pnl_rate = (total_pnl_amount / total_invested * 100) if total_invested else _ZERO

    allocation = _build_allocation(holding_items, total_asset, price_result.exchange_rate)

    # 포트폴리오 전일 대비: 시가총액 가중 평균
    total_day_change_rate: Optional[Decimal] = None
    weighted_sum = _ZERO
    weight_total = _ZERO
    for item in holding_items:
        if item.day_change_rate is not None and item.market_value_krw is not None:
            weighted_sum += item.day_change_rate * item.market_value_krw
            weight_total += item.market_value_krw
    if weight_total > _ZERO:
        total_day_change_rate = weighted_sum / weight_total

    exchange_rate = price_result.exchange_rate
    overseas_tickers = [h.ticker for h in holdings if not is_domestic(h.ticker)]

    # KIS 실시간 API prev_close 기반 전일 대비 계산.
    # DB 스냅샷 대신 실시간 API의 전일종가를 사용해 타임존 불일치 문제를 방지한다.
    # (스냅샷은 KST 16:10 = UTC 07:10에 저장되므로 미국장 마감 전 데이터가 들어감)
    day_change_pct: Optional[Decimal] = None
    day_change_amount: Optional[Decimal] = None
    api_prev_closes = price_result.prev_closes
    if api_prev_closes and total_asset > _ZERO:
        prev_total = _ZERO
        curr_total = _ZERO
        for item in holding_items:
            prev_close = api_prev_closes.get(item.ticker)
            if prev_close is None or prev_close <= _ZERO:
                continue
            if item.currency == "USD":
                if item.market_value_krw is None:
                    continue
                prev_total += item.quantity * prev_close * exchange_rate
                curr_total += item.market_value_krw
            else:
                if item.market_value is None:
                    continue
                prev_total += item.quantity * prev_close
                curr_total += item.market_value
        if prev_total > _ZERO:
            day_change_amount = curr_total - prev_total
            day_change_pct = day_change_amount / prev_total * 100

    # 목표가 알림 확인
    alert_result = await db.execute(
        select(Alert).where(Alert.user_id == current_user.id, Alert.is_active.is_(True))
    )
    active_alerts = list(alert_result.scalars().all())
    avg_prices_map: dict[str, Optional[Decimal]] = {}
    for h in holdings:
        avg_prices_map.setdefault(h.ticker, h.avg_price)
    triggered_raw = check_triggered_alerts(
        active_alerts,
        price_result.prices,
        avg_prices=avg_prices_map,
        day_change_pcts=price_result.day_change_rates,
    )
    triggered_alerts = [TriggeredAlert(**a) for a in triggered_raw]

    summary = DashboardSummary(
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
        kis_status=price_result.kis_status,
    )

    # ETag / 304 Not Modified — skip during force-refresh to always return fresh data
    if not refresh:
        body = json.dumps(summary.model_dump(mode="json"), default=str, sort_keys=True)
        etag = hashlib.sha256(body.encode()).hexdigest()[:16]
        if_none_match = request.headers.get("if-none-match", "")
        if if_none_match == etag:
            return FastAPIResponse(status_code=304, headers={"ETag": etag})
        return FastAPIResponse(
            content=body,
            media_type="application/json",
            headers={"ETag": etag},
        )

    return summary
