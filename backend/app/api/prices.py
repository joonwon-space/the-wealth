"""가격 히스토리 API."""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    limit: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """종목 일별 종가 히스토리 조회.

    - `from`: 시작일 (inclusive), 기본값 없음
    - `to`: 종료일 (inclusive), 기본값 없음
    - `limit`: 최대 반환 건수 (기본 90일, 최대 365일)
    """
    stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker == ticker.upper())
        .order_by(PriceSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    if from_date:
        stmt = stmt.where(PriceSnapshot.snapshot_date >= from_date)
    if to_date:
        stmt = stmt.where(PriceSnapshot.snapshot_date <= to_date)

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        {
            "date": snap.snapshot_date.isoformat(),
            "close": str(Decimal(str(snap.close))),
        }
        for snap in sorted(snapshots, key=lambda s: s.snapshot_date)
    ]
