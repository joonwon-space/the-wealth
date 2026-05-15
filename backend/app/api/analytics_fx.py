"""환차손익 API — fx-gain-loss, fx-history."""

import asyncio
import bisect
import json
from datetime import date as date_type, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from app.models.user import User
from app.schemas.analytics import FxGainLossItem
from app.services.analytics_utils import (
    ANALYTICS_CACHE_TTL,
    analytics_key,
    get_analytics_cache,
)
from app.services.kis_price import _get_cached_price, get_cached_fx_rate

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)


@router.get("/fx-gain-loss", response_model=list[FxGainLossItem])
@limiter.limit("30/minute")
async def get_fx_gain_loss(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FastAPIResponse:
    """해외주식 보유 종목별 환차익/환차손 분리 계산 (ETag/304 적용).

    각 해외주식에 대해 주가 수익(USD 기준)과 환차익(KRW 기준)을 분리하여 반환한다.
    - 주가 수익 = (현재가 - 매입가) × 수량 (USD)
    - 환차익 = 매입 원금 × (현재 환율 / 매입 시 환율 - 1) (KRW)

    매입 시 환율: 보유 종목 created_at 날짜에 가장 가까운 fx_rate_snapshots 환율 사용.
    현재가: Redis 캐시 우선, 없으면 avg_price fallback.
    현재 환율: Redis 캐시(get_cached_fx_rate) 사용.
    """
    _cache = get_analytics_cache()
    cache_key = analytics_key(current_user.id, "fx-gain-loss")
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
    all_holdings = hold_result.scalars().all()

    # 해외주식만 필터링 (ticker가 숫자 6자리가 아닌 경우)
    overseas = [h for h in all_holdings if not is_domestic(h.ticker)]
    if not overseas:
        return etag_response(request, [])

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
        idx = bisect.bisect_left(fx_dates_sorted, target_date)
        candidates: list[float] = []
        if idx < len(fx_dates_sorted):
            candidates.append(fx_date_map[fx_dates_sorted[idx]])
        if idx > 0:
            candidates.append(fx_date_map[fx_dates_sorted[idx - 1]])
        if not candidates:
            return fx_current
        if len(candidates) == 1:
            return candidates[0]
        d0 = abs((date_type.fromisoformat(fx_dates_sorted[max(0, idx - 1)]) -
                  date_type.fromisoformat(target_date)).days)
        d1 = abs((date_type.fromisoformat(fx_dates_sorted[min(len(fx_dates_sorted) - 1, idx)]) -
                  date_type.fromisoformat(target_date)).days)
        return candidates[1] if d0 <= d1 else candidates[0]

    # 현재가 병렬 조회 (sequential 대신 gather로 최적화)
    cached_prices = await asyncio.gather(*[_get_cached_price(h.ticker) for h in overseas])

    result_items: list[FxGainLossItem] = []
    for h, cached_price in zip(overseas, cached_prices):
        # 현재가 (USD)
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

        result_items.append(FxGainLossItem(
            ticker=h.ticker,
            name=h.name,
            quantity=qty,
            avg_price_usd=round(avg_price_usd, 4),
            current_price_usd=round(current_price_usd, 4),
            stock_pnl_usd=round(stock_pnl_usd, 2),
            fx_rate_at_buy=round(fx_at_buy, 2),
            fx_rate_current=round(fx_current, 2),
            fx_gain_krw=round(fx_gain_krw, 0),
            stock_gain_krw=round(stock_gain_krw, 0),
            total_pnl_krw=round(total_pnl_krw, 0),
        ))

    payload = [item.model_dump() for item in result_items]
    await _cache.setex(cache_key, ANALYTICS_CACHE_TTL, json.dumps(payload))
    return etag_response(request, payload)


@router.get("/fx-history")
@limiter.limit("30/minute")
async def get_fx_history(
    request: Request,
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
    _valid_pairs = {"USDKRW", "EURKRW", "JPYKRW", "CNYKRW"}
    if currency_pair not in _valid_pairs:
        raise HTTPException(status_code=400, detail=f"currency_pair must be one of: {', '.join(sorted(_valid_pairs))}")

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
