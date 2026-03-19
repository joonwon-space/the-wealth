"""데이터 무결성 헬스체크 API."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User

router = APIRouter(prefix="/health", tags=["health"])


def _last_n_weekdays(n: int, reference: date) -> list[date]:
    """reference 날짜 이전 n개의 평일(월~금) 반환 (reference 포함 가능)."""
    days: list[date] = []
    current = reference
    while len(days) < n:
        if current.weekday() < 5:  # 0=월 ~ 4=금
            days.append(current)
        current -= timedelta(days=1)
    return days


@router.get("/data-integrity")
async def data_integrity_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """price_snapshots 갭 감지 헬스체크.

    최근 7 평일 중 스냅샷이 없는 날짜를 반환한다.
    응답 예시:
    {
      "status": "ok" | "degraded",
      "checked_weekdays": 7,
      "missing_snapshots": ["2026-03-18"],
      "present_snapshots": ["2026-03-17", ...]
    }
    """
    today = date.today()
    weekdays = _last_n_weekdays(7, today)

    # 해당 날짜에 스냅샷이 존재하는지 확인 (ticker 무관, 최소 1건)
    result = await db.execute(
        select(PriceSnapshot.snapshot_date)
        .where(PriceSnapshot.snapshot_date.in_(weekdays))
        .group_by(PriceSnapshot.snapshot_date)
        .having(func.count() > 0)
    )
    present_dates = {row[0] for row in result.all()}

    missing: list[str] = []
    present: list[str] = []
    for d in sorted(weekdays):
        if d in present_dates:
            present.append(d.isoformat())
        else:
            missing.append(d.isoformat())

    status = "ok" if not missing else "degraded"
    return {
        "status": status,
        "checked_weekdays": len(weekdays),
        "missing_snapshots": missing,
        "present_snapshots": present,
    }
