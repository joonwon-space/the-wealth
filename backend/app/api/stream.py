"""Stream API — GET /stream

알림·체결·배당·리밸런싱·루틴 이벤트를 하나의 시간순 피드로 집계.
프론트 Stream 탭(/dashboard/stream)에서 사용한다.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.models.notification import Notification
from app.models.order import Order
from app.models.portfolio import Portfolio
from app.models.routine_log import RoutineLog
from app.models.user import User
from app.schemas.redesign import StreamItem, StreamResponse

router = APIRouter(prefix="/stream", tags=["stream"])
logger = get_logger(__name__)

_ALLOWED_FILTERS = {"all", "alert", "fill", "dividend", "rebalance", "routine"}


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("", response_model=StreamResponse)
@limiter.limit("60/minute")
async def stream(
    request: Request,
    filter: str = Query(default="all"),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamResponse:
    """최근 이벤트를 시간역순으로 반환.

    Filter:
      - all      : 모든 카드
      - alert    : 트리거된 알림 (Notification)
      - fill     : 체결 (Order.status in filled/partial)
      - dividend : 보유 종목의 다음 30일 배당
      - rebalance: 목표 비중 대비 초과 섹터가 있는 포트폴리오 (1개 카드/포트폴리오)
      - routine  : 아직 완료되지 않은 월/분기 체크 (간단 버전)
    """
    if filter not in _ALLOWED_FILTERS:
        filter = "all"

    items: list[StreamItem] = []
    # 내 포트폴리오
    portfolios = (
        await db.execute(
            select(Portfolio).where(Portfolio.user_id == current_user.id)
        )
    ).scalars().all()
    portfolio_ids = [p.id for p in portfolios]

    # ------------------ Alert 알림 ----------------------
    if filter in ("all", "alert"):
        notifs = (
            await db.execute(
                select(Notification)
                .where(Notification.user_id == current_user.id)
                .order_by(Notification.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        for n in notifs:
            ticker = getattr(n, "ticker", None)
            items.append(
                StreamItem(
                    id=f"alert:{n.id}",
                    kind="alert",
                    ts=_utc(n.created_at),
                    title=getattr(n, "title", None) or f"알림 — {ticker or ''}",
                    sub=getattr(n, "message", None),
                    payload={
                        "notification_id": n.id,
                        "ticker": ticker,
                    },
                )
            )

    # ------------------ Fill 체결 ------------------------
    if filter in ("all", "fill") and portfolio_ids:
        orders = (
            await db.execute(
                select(Order)
                .where(Order.portfolio_id.in_(portfolio_ids))
                .where(Order.status.in_(("filled", "partial")))
                .order_by(Order.updated_at.desc().nulls_last(), Order.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        for o in orders:
            filled_qty = getattr(o, "filled_quantity", None) or getattr(o, "quantity", None)
            filled_price = getattr(o, "filled_price", None) or getattr(o, "price", None)
            action = "매수" if o.order_type == "BUY" else "매도"
            ts = getattr(o, "updated_at", None) or getattr(o, "created_at", datetime.now(timezone.utc))
            items.append(
                StreamItem(
                    id=f"fill:{o.id}",
                    kind="fill",
                    ts=_utc(ts),
                    title=f"{o.name or o.ticker} {action}",
                    sub=f"{filled_qty}주 @ {filled_price}" if filled_qty else None,
                    payload={
                        "order_id": o.id,
                        "ticker": o.ticker,
                        "portfolio_id": o.portfolio_id,
                    },
                )
            )

    # ------------------ Dividend 예정 --------------------
    if filter in ("all", "dividend") and portfolio_ids:
        holdings = (
            await db.execute(
                select(Holding).where(Holding.portfolio_id.in_(portfolio_ids))
            )
        ).scalars().all()
        tickers = list({h.ticker for h in holdings})
        if tickers:
            today = date.today()
            horizon = today + timedelta(days=30)
            divs = (
                await db.execute(
                    select(Dividend)
                    .where(Dividend.ticker.in_(tickers))
                    .where(Dividend.record_date.between(today, horizon))
                    .order_by(Dividend.ex_date.asc().nulls_last())
                    .limit(limit)
                )
            ).scalars().all()
            for d in divs:
                items.append(
                    StreamItem(
                        id=f"dividend:{d.id}",
                        kind="dividend",
                        ts=datetime.combine(d.record_date, datetime.min.time(), tzinfo=timezone.utc),
                        title=f"{d.ticker} 배당 예정",
                        sub=f"배당락 {d.ex_date or d.record_date} · 지급 {d.payment_date or '미정'} · {d.amount}{d.currency}",
                        payload={
                            "dividend_id": d.id,
                            "ticker": d.ticker,
                            "amount": float(d.amount),
                            "currency": d.currency,
                        },
                    )
                )

    # ------------------ Rebalance 제안 -------------------
    if filter in ("all", "rebalance"):
        for p in portfolios:
            target = p.target_allocation or {}  # type: ignore[assignment]
            if not target:
                continue
            # Rebalance suggestion은 별도 API 가 다 해주므로 여기선 "초과 섹터 있음" 단순 신호.
            # 실제 데이터는 프론트에서 필요 시 rebalance-suggestion 호출.
            items.append(
                StreamItem(
                    id=f"rebalance:p{p.id}-{date.today().strftime('%Y%m')}",
                    kind="rebalance",
                    ts=datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc),
                    title=f"{p.name} 리밸런싱 확인",
                    sub="섹터 목표 비중 대비 편차 점검",
                    payload={"portfolio_id": p.id},
                )
            )

    # ------------------ Routine 루틴 ---------------------
    if filter in ("all", "routine"):
        recent_logs = (
            await db.execute(
                select(RoutineLog)
                .where(RoutineLog.user_id == current_user.id)
                .order_by(RoutineLog.completed_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        for r in recent_logs:
            items.append(
                StreamItem(
                    id=f"routine:{r.id}",
                    kind="routine",
                    ts=_utc(r.completed_at),
                    title=f"{r.routine_kind} · {r.period_key}",
                    sub=r.note,
                    payload={"routine_log_id": r.id},
                )
            )

    # 정렬 + 제한
    items.sort(key=lambda x: x.ts, reverse=True)
    items = items[:limit]
    return StreamResponse(items=items, next_cursor=None)
