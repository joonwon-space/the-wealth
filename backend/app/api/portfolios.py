"""Portfolio CRUD endpoints — create, list, update, delete, reorder."""

import asyncio
import json
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._etag import etag_response
from app.api.analytics import invalidate_analytics_cache
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.encryption import decrypt
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.redis_cache import RedisCache
from app.core.ticker import is_domestic
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
    PortfolioWithPricesResponse,
    ReorderRequest,
)
from app.services.kis_price import (
    fetch_usd_krw_rate,
    get_or_fetch_domestic_price,
    get_or_fetch_overseas_price,
)

_MARKET_MAP = {
    "NASD": "NAS", "NYSE": "NYS", "AMEX": "AMS",
    "SEHK": "HKS", "TKSE": "TSE", "SHAA": "SHS",
    "SZAA": "SZS", "HASE": "HNX", "VNSE": "HSX",
}

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = get_logger(__name__)

_cache = RedisCache(settings.REDIS_URL)
_PWP_CACHE_PREFIX = "pwp:user:{user_id}"  # /portfolios/with-prices response cache
_PWP_CACHE_TTL = 30  # seconds — matches holdings price TTL during market hours


async def invalidate_portfolios_with_prices_cache(user_id: int) -> None:
    """holdings/orders/sync 변경 시 응답 캐시 무효화."""
    await _cache.delete(_PWP_CACHE_PREFIX.format(user_id=user_id))


def _assert_portfolio_owner(portfolio: Portfolio, user: User) -> None:
    if portfolio.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    # Single query with LEFT JOIN + GROUP BY instead of N+1
    stmt = (
        select(
            Portfolio,
            KisAccount.label,
            func.count(Holding.id).label("holdings_count"),
            func.coalesce(
                func.sum(Holding.quantity * Holding.avg_price), Decimal("0")
            ).label("total_invested"),
        )
        .outerjoin(KisAccount, KisAccount.id == Portfolio.kis_account_id)
        .outerjoin(Holding, Holding.portfolio_id == Portfolio.id)
        .where(Portfolio.user_id == current_user.id)
        .group_by(Portfolio.id, KisAccount.label)
        .order_by(Portfolio.display_order.asc(), Portfolio.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "name": kis_label if kis_label else p.name,
            "currency": p.currency,
            "display_order": p.display_order,
            "created_at": p.created_at,
            "holdings_count": count,
            "total_invested": invested,
            "kis_account_id": p.kis_account_id,
            "target_value": p.target_value,
        }
        for p, kis_label, count, invested in rows
    ]


@router.get("/with-prices", response_model=list[PortfolioWithPricesResponse])
@limiter.limit("10/minute")
async def list_portfolios_with_prices(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All portfolios with aggregated KIS real-time prices, KRW-normalized.

    Price fields are None when KIS is not connected or the call fails.
    De-duplicates tickers across portfolios before KIS requests to stay within
    the rate limit.

    Response 자체를 Redis 캐시 (pwp:user:{id}, 30s TTL) — 같은 사용자가 빠르게
    재진입해도 DB query + KIS cache lookup + 집계를 모두 skip. holdings/orders/sync
    변경 시 호출자가 invalidate_portfolios_with_prices_cache 호출해 무효화.
    ETag/304 로 클라이언트 측 재전송도 차단.
    """
    cache_key = _PWP_CACHE_PREFIX.format(user_id=current_user.id)
    cached_raw = await _cache.get(cache_key)
    if cached_raw:
        try:
            cached_payload = json.loads(cached_raw)
            return etag_response(request, cached_payload)
        except json.JSONDecodeError:
            pass  # malformed → refetch

    # 1. Fetch all portfolios with holding counts and total_invested (same query as list)
    stmt = (
        select(
            Portfolio,
            KisAccount.label,
            func.count(Holding.id).label("holdings_count"),
            func.coalesce(
                func.sum(Holding.quantity * Holding.avg_price), Decimal("0")
            ).label("total_invested"),
        )
        .outerjoin(KisAccount, KisAccount.id == Portfolio.kis_account_id)
        .outerjoin(Holding, Holding.portfolio_id == Portfolio.id)
        .where(Portfolio.user_id == current_user.id)
        .group_by(Portfolio.id, KisAccount.label)
        .order_by(Portfolio.display_order.asc(), Portfolio.created_at.asc())
    )
    portfolio_rows = list((await db.execute(stmt)).all())
    if not portfolio_rows:
        # 빈 응답도 캐시 — invalidate 는 portfolio 생성 시점에 발생
        await _cache.setex(cache_key, _PWP_CACHE_TTL, "[]")
        return etag_response(request, [])

    portfolio_ids = [p.id for p, *_ in portfolio_rows]

    # 2. Fetch all holdings for all user portfolios in one query
    holdings_result = await db.execute(
        select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
    )
    all_holdings = list(holdings_result.scalars().all())

    # Group holdings by portfolio id for easy lookup
    holdings_by_portfolio: dict[int, list[Holding]] = {pid: [] for pid in portfolio_ids}
    for h in all_holdings:
        holdings_by_portfolio[h.portfolio_id].append(h)

    # 3. Deduplicate tickers across all portfolios
    all_domestic: set[str] = set()
    all_overseas: set[str] = set()
    ticker_to_market: dict[str, str] = {}
    for h in all_holdings:
        if is_domestic(h.ticker):
            all_domestic.add(h.ticker)
        else:
            all_overseas.add(h.ticker)
            ticker_to_market[h.ticker] = _MARKET_MAP.get(
                h.market or "", h.market or "NAS"
            )

    # 4. Resolve a KIS account for the user
    acct: KisAccount | None = None
    if portfolio_rows:
        for p, *_ in portfolio_rows:
            if p.kis_account_id:
                acct = await db.get(KisAccount, p.kis_account_id)
                if acct:
                    break
    if acct is None and all_holdings:
        fallback = await db.execute(
            select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
        )
        acct = fallback.scalar_one_or_none()

    # 5. Fetch prices + FX rate in parallel (all unique tickers at once)
    prices: dict[str, Decimal | None] = {}
    exchange_rate: Decimal = Decimal("1450")

    if acct and all_holdings:
        try:
            app_key = decrypt(acct.app_key_enc)
            app_secret = decrypt(acct.app_secret_enc)
            domestic_list = list(all_domestic)
            overseas_list = list(all_overseas)
            async with httpx.AsyncClient(timeout=10.0) as client:
                domestic_tasks = [
                    get_or_fetch_domestic_price(t, app_key, app_secret, client)
                    for t in domestic_list
                ]
                overseas_tasks = [
                    get_or_fetch_overseas_price(
                        t, ticker_to_market[t], app_key, app_secret, client
                    )
                    for t in overseas_list
                ]
                fx_task = (
                    fetch_usd_krw_rate(app_key, app_secret, client)
                    if overseas_list
                    else asyncio.sleep(0, result=Decimal("1450"))
                )
                *all_prices, fx = await asyncio.gather(
                    *domestic_tasks, *overseas_tasks, fx_task,
                    return_exceptions=True,
                )
            for ticker, price in zip(domestic_list, all_prices[: len(domestic_list)]):
                if isinstance(price, Decimal) and price > 0:
                    prices[ticker] = price
            for ticker, price in zip(overseas_list, all_prices[len(domestic_list):]):
                if isinstance(price, Decimal) and price > 0:
                    prices[ticker] = price
            if isinstance(fx, Decimal) and fx > 0:
                exchange_rate = fx
        except Exception as e:
            logger.warning("Failed to fetch prices for portfolios/with-prices: %s", e)

    # 6. Aggregate per-portfolio
    results: list[dict] = []
    for p, kis_label, count, invested in portfolio_rows:
        holdings = holdings_by_portfolio[p.id]
        portfolio_name = kis_label if kis_label else p.name

        market_value_krw: Decimal | None = None
        pnl_amount_krw: Decimal | None = None
        pnl_rate: Decimal | None = None

        if holdings:
            mv_total = Decimal("0")
            inv_total = Decimal("0")
            has_prices = False

            for h in holdings:
                cp = prices.get(h.ticker)
                is_os = not is_domestic(h.ticker)
                h_invested = h.quantity * h.avg_price
                if cp is not None:
                    has_prices = True
                    if is_os:
                        inv_total += h_invested * exchange_rate
                        mv_total += h.quantity * cp * exchange_rate
                    else:
                        inv_total += h_invested
                        mv_total += h.quantity * cp

            if has_prices and inv_total > 0:
                market_value_krw = mv_total
                pnl_amount_krw = mv_total - inv_total
                pnl_rate = pnl_amount_krw / inv_total * Decimal("100")
            elif has_prices:
                market_value_krw = mv_total

        results.append({
            "id": p.id,
            "user_id": p.user_id,
            "name": portfolio_name,
            "currency": p.currency,
            "display_order": p.display_order,
            "created_at": p.created_at,
            "holdings_count": count,
            "total_invested": invested,
            "kis_account_id": p.kis_account_id,
            "target_value": p.target_value,
            "market_value_krw": market_value_krw,
            "pnl_amount_krw": pnl_amount_krw,
            "pnl_rate": pnl_rate,
            "exchange_rate": exchange_rate if all_overseas and acct else None,
        })

    # 응답 캐시 — json.dumps default=str 로 Decimal/datetime 자동 변환
    try:
        await _cache.setex(cache_key, _PWP_CACHE_TTL, json.dumps(results, default=str))
    except (TypeError, ValueError) as e:
        logger.warning("Failed to cache /portfolios/with-prices for user %d: %s", current_user.id, e)

    return etag_response(request, results)


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_portfolio(
    request: Request,
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Portfolio:
    max_order_result = await db.execute(
        select(func.max(Portfolio.display_order)).where(Portfolio.user_id == current_user.id)
    )
    max_order = max_order_result.scalar() or -1
    portfolio = Portfolio(
        user_id=current_user.id,
        name=body.name,
        currency=body.currency,
        display_order=max_order + 1,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    await invalidate_portfolios_with_prices_cache(current_user.id)
    return portfolio


@router.patch("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_portfolios(
    body: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """포트폴리오 순서 일괄 업데이트. IDOR 방지: 본인 포트폴리오만 허용."""
    ids = [item.id for item in body.items]
    result = await db.execute(
        select(Portfolio).where(Portfolio.id.in_(ids), Portfolio.user_id == current_user.id)
    )
    owned = {p.id for p in result.scalars().all()}
    if owned != set(ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    for item in body.items:
        await db.execute(
            Portfolio.__table__.update()
            .where(Portfolio.id == item.id)
            .values(display_order=item.display_order)
        )
    await db.commit()
    await invalidate_portfolios_with_prices_cache(current_user.id)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    body: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    if body.name is not None:
        portfolio.name = body.name
    if body.currency is not None:
        portfolio.currency = body.currency
    if "target_value" in body.model_fields_set:
        portfolio.target_value = body.target_value

    # Sync KIS account label if linked and name changed
    if body.name is not None and portfolio.kis_account_id:
        acct = await db.get(KisAccount, portfolio.kis_account_id)
        if acct:
            acct.label = body.name

    await db.commit()
    await db.refresh(portfolio)
    await invalidate_analytics_cache(current_user.id)
    await invalidate_portfolios_with_prices_cache(current_user.id)

    stats = await db.execute(
        select(
            func.count(Holding.id),
            func.coalesce(func.sum(Holding.quantity * Holding.avg_price), Decimal("0")),
        ).where(Holding.portfolio_id == portfolio.id)
    )
    count, invested = stats.one()
    return {
        "id": portfolio.id,
        "user_id": portfolio.user_id,
        "name": portfolio.name,
        "currency": portfolio.currency,
        "display_order": portfolio.display_order,
        "created_at": portfolio.created_at,
        "holdings_count": count,
        "total_invested": invested,
        "target_value": portfolio.target_value,
    }


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_portfolio(
    request: Request,
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    _assert_portfolio_owner(portfolio, current_user)
    await db.delete(portfolio)
    await db.commit()
    await invalidate_portfolios_with_prices_cache(current_user.id)
