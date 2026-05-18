"""Tasks API — GET /tasks/today

홈 hero 아래 "오늘 할 것 N" 카드 피드를 집계. 소스:
  - 오늘/내일 배당락일이 있는 보유 종목
  - 활성 알림 중 최근 조건 근처(±5%) 인 종목
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.redesign import HomeTask, TodayTasksResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)


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

    tasks.sort(key=lambda t: t.priority, reverse=True)
    return TodayTasksResponse(count=len(tasks), tasks=tasks)
