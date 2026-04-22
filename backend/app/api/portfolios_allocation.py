"""포트폴리오 목표 비중 + 리밸런싱 제안 API.

redesign-spec.md §1.4 의 아래 2개 엔드포인트를 구현한다:
  PUT  /portfolios/{id}/target-allocation
  GET  /portfolios/{id}/rebalance-suggestion
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.ticker import is_domestic
from app.data.sector_map import get_sector
from app.db.session import get_db
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.redesign import (
    RebalanceCandidate,
    RebalanceSuggestionResponse,
    RebalanceSuggestionRow,
    TargetAllocationResponse,
    TargetAllocationUpdate,
)
from app.services.kis_price import fetch_usd_krw_rate

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = get_logger(__name__)


async def _load_owned(db: AsyncSession, portfolio_id: int, user: User) -> Portfolio:
    row = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = row.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="포트폴리오를 찾을 수 없습니다.")
    if portfolio.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    return portfolio


@router.put(
    "/{portfolio_id}/target-allocation",
    response_model=TargetAllocationResponse,
)
@limiter.limit("30/minute")
async def update_target_allocation(
    request: Request,
    portfolio_id: int,
    body: TargetAllocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TargetAllocationResponse:
    """섹터별 목표 비중 저장."""
    portfolio = await _load_owned(db, portfolio_id, current_user)
    portfolio.target_allocation = dict(body.target_allocation)
    await db.commit()
    await db.refresh(portfolio)
    return TargetAllocationResponse(
        portfolio_id=portfolio.id,
        target_allocation=portfolio.target_allocation,  # type: ignore[arg-type]
    )


@router.get(
    "/{portfolio_id}/target-allocation",
    response_model=TargetAllocationResponse,
)
async def get_target_allocation(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TargetAllocationResponse:
    portfolio = await _load_owned(db, portfolio_id, current_user)
    return TargetAllocationResponse(
        portfolio_id=portfolio.id,
        target_allocation=portfolio.target_allocation,  # type: ignore[arg-type]
    )


@router.get(
    "/{portfolio_id}/rebalance-suggestion",
    response_model=RebalanceSuggestionResponse,
)
@limiter.limit("30/minute")
async def rebalance_suggestion(
    request: Request,
    portfolio_id: int,
    threshold: float = 0.03,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RebalanceSuggestionResponse:
    """현재 섹터 비중 vs Portfolio.target_allocation 차이를 계산하고 제안 주문을 낸다.

    동작:
      1. 보유 종목의 섹터별 현재 가치(원화 환산)를 집계.
      2. target_allocation 과 비교해 threshold 를 넘는 섹터만 조정 대상.
      3. 초과 섹터 → 큰 포지션부터 SELL 후보 / 부족 섹터 → 작은 포지션부터 BUY 후보.
    """
    portfolio = await _load_owned(db, portfolio_id, current_user)
    target: dict[str, float] = portfolio.target_allocation or {}  # type: ignore[assignment]

    # --- 현재가치 집계 -----------------------------------------------------
    hold_res = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    )
    holdings = hold_res.scalars().all()
    if not holdings:
        return RebalanceSuggestionResponse(
            portfolio_id=portfolio.id, total_value_krw=0.0, rows=[]
        )

    try:
        usd_krw = await fetch_usd_krw_rate()
    except Exception:  # noqa: BLE001 — KIS 환율 조회 실패 시 1USD=1KRW 로 보수적 계산
        usd_krw = 1.0

    sector_values: dict[str, float] = {}
    sector_holdings: dict[str, list[tuple[Holding, float]]] = {}
    for h in holdings:
        sector = get_sector(h.ticker)
        value_local = float(h.quantity) * float(h.avg_price)
        value = value_local if is_domestic(h.ticker) else value_local * float(usd_krw)
        sector_values[sector] = sector_values.get(sector, 0.0) + value
        sector_holdings.setdefault(sector, []).append((h, value))

    total_value = sum(sector_values.values())
    if total_value <= 0:
        return RebalanceSuggestionResponse(
            portfolio_id=portfolio.id, total_value_krw=0.0, rows=[]
        )

    # --- 비교 + 제안 ----------------------------------------------------
    rows: list[RebalanceSuggestionRow] = []
    sectors = set(sector_values.keys()) | set(target.keys())
    for sector in sorted(sectors):
        current_pct = sector_values.get(sector, 0.0) / total_value
        target_pct = float(target.get(sector, 0.0))
        diff_pct = current_pct - target_pct
        action = "HOLD"
        if diff_pct > threshold:
            action = "SELL"
        elif diff_pct < -threshold:
            action = "BUY"
        delta_krw = diff_pct * total_value

        # 후보: SELL 섹터면 보유 비중 큰 순, BUY 섹터면 보유 비중 작은 순
        candidates: list[RebalanceCandidate] = []
        if action != "HOLD":
            sector_list = sector_holdings.get(sector, [])
            sorted_list = sorted(
                sector_list,
                key=lambda x: x[1],
                reverse=(action == "SELL"),
            )
            for holding, value in sorted_list[:3]:
                weight_in_sector = (
                    value / sector_values[sector] if sector in sector_values else 0.0
                )
                # 제안 수량 = (이 후보에 배분된 금액) / 평균가
                allocated_krw = abs(delta_krw) * weight_in_sector
                price = float(holding.avg_price)
                if not is_domestic(holding.ticker):
                    price *= float(usd_krw)
                qty = allocated_krw / price if price > 0 else 0.0
                candidates.append(
                    RebalanceCandidate(
                        ticker=holding.ticker,
                        name=holding.name,
                        weight_in_sector=round(weight_in_sector, 4),
                        suggested_qty=round(qty, 4),
                        suggested_action="BUY" if action == "BUY" else "SELL",
                    )
                )

        rows.append(
            RebalanceSuggestionRow(
                sector=sector,
                current_pct=round(current_pct, 4),
                target_pct=round(target_pct, 4),
                diff_pct=round(diff_pct, 4),
                delta_krw=round(delta_krw, 0),
                suggested_action=action,
                candidates=candidates,
            )
        )

    # 우선순위: |diff_pct| 큰 순
    rows.sort(key=lambda r: abs(r.diff_pct), reverse=True)
    return RebalanceSuggestionResponse(
        portfolio_id=portfolio.id,
        total_value_krw=round(total_value, 0),
        rows=rows,
    )
