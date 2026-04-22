"""Tasks API — GET /tasks/today

홈 hero 아래 "오늘 할 것 N" 카드 피드를 집계. 소스:
  - Portfolio.target_allocation 이 설정돼 있고 실제 비중이 임계치를 넘는 경우
  - 오늘/내일 배당락일이 있는 보유 종목
  - 활성 알림 중 최근 조건 근처(±5%) 인 종목
  - 아직 완료하지 않은 월 리밸런싱 루틴
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.core.ticker import is_domestic
from app.data.sector_map import get_sector
from app.db.session import get_db
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.routine_log import RoutineLog
from app.models.user import User
from app.schemas.redesign import HomeTask, TodayTasksResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)

_REBALANCE_THRESHOLD = 0.05


@router.get("/today", response_model=TodayTasksResponse)
@limiter.limit("60/minute")
async def today_tasks(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodayTasksResponse:
    tasks: list[HomeTask] = []

    portfolios = (
        await db.execute(
            select(Portfolio).where(Portfolio.user_id == current_user.id)
        )
    ).scalars().all()

    # ------------------ 리밸런싱 점검 ------------------
    for p in portfolios:
        target: dict[str, float] = p.target_allocation or {}  # type: ignore[assignment]
        if not target:
            continue
        holdings = (
            await db.execute(
                select(Holding).where(Holding.portfolio_id == p.id)
            )
        ).scalars().all()
        if not holdings:
            continue
        sector_values: dict[str, float] = {}
        for h in holdings:
            value_local = float(h.quantity) * float(h.avg_price)
            # FX 생략 — 여기선 오차보단 태스크 등장 여부가 더 중요.
            if not is_domestic(h.ticker):
                value_local *= 1300.0  # 보수적 고정 환율 (실제 사용 시 fx_rate)
            sector_values[get_sector(h.ticker)] = (
                sector_values.get(get_sector(h.ticker), 0.0) + value_local
            )
        total = sum(sector_values.values())
        if total <= 0:
            continue
        over_sectors: list[tuple[str, float]] = []
        for sector, v in sector_values.items():
            current_pct = v / total
            target_pct = float(target.get(sector, 0.0))
            diff = current_pct - target_pct
            if abs(diff) >= _REBALANCE_THRESHOLD:
                over_sectors.append((sector, diff))
        if over_sectors:
            # 편차 가장 큰 섹터를 타이틀로.
            over_sectors.sort(key=lambda t: abs(t[1]), reverse=True)
            lead = over_sectors[0]
            sign = "+" if lead[1] > 0 else ""
            tasks.append(
                HomeTask(
                    id=f"rebalance:p{p.id}",
                    kind="rebalance",
                    title=f"{p.name} 리밸런싱 필요",
                    sub=f"{lead[0]} {sign}{lead[1] * 100:.0f}%p",
                    accent="var(--accent-amber)",
                    priority=80,
                )
            )

    # ------------------ 배당락 근접 --------------------
    if portfolios:
        holdings_all = (
            await db.execute(
                select(Holding).where(
                    Holding.portfolio_id.in_([p.id for p in portfolios])
                )
            )
        ).scalars().all()
        tickers = {h.ticker for h in holdings_all}
        if tickers:
            today = date.today()
            horizon = today + timedelta(days=7)
            divs = (
                await db.execute(
                    select(Dividend)
                    .where(Dividend.ticker.in_(tickers))
                    .where(Dividend.record_date.between(today, horizon))
                    .order_by(Dividend.ex_date.asc().nulls_last())
                    .limit(5)
                )
            ).scalars().all()
            for d in divs:
                tasks.append(
                    HomeTask(
                        id=f"dividend:{d.id}",
                        kind="dividend",
                        title=f"{d.ticker} 배당락 접근",
                        sub=f"{d.ex_date or d.record_date} · {d.amount}{d.currency}",
                        accent="var(--primary)",
                        priority=60,
                    )
                )

    # ------------------ 월 리밸런싱 루틴 ----------------
    period_key = date.today().strftime("%Y-%m")
    existing = (
        await db.execute(
            select(RoutineLog.id)
            .where(RoutineLog.user_id == current_user.id)
            .where(RoutineLog.routine_kind == "rebalance_monthly")
            .where(RoutineLog.period_key == period_key)
        )
    ).scalar_one_or_none()
    if existing is None and portfolios:
        tasks.append(
            HomeTask(
                id=f"routine:monthly-{period_key}",
                kind="routine",
                title=f"{period_key[-2:]}월 리밸런싱 체크",
                sub="이번 달 아직 체크하지 않았습니다",
                accent="var(--chart-6)",
                priority=40,
            )
        )

    tasks.sort(key=lambda t: t.priority, reverse=True)
    return TodayTasksResponse(count=len(tasks), tasks=tasks)
