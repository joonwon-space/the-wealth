"""벤치마크 지수 히스토리 API — GET /analytics/benchmark."""

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.index_snapshot import IndexSnapshot
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)

_VALID_INDEX_CODES = {"KOSPI200", "SP500"}


@router.get("/benchmark")
@limiter.limit("30/minute")
async def get_benchmark(
    request: Request,
    index_code: str = Query(
        default="KOSPI200",
        description="지수 코드: KOSPI200 | SP500",
    ),
    from_date: Optional[date_type] = Query(
        default=None,
        alias="from",
        description="조회 시작일 (YYYY-MM-DD)",
    ),
    to_date: Optional[date_type] = Query(
        default=None,
        alias="to",
        description="조회 종료일 (YYYY-MM-DD)",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """벤치마크 지수 일별 종가 시계열 반환.

    index_snapshots 테이블에서 지정 지수의 날짜별 종가를 조회하여
    [{date, close_price}] 형태로 반환한다.

    쿼리 파라미터:
    - index_code: 지수 코드 (KOSPI200 | SP500, 기본값 KOSPI200)
    - from: 조회 시작일 (YYYY-MM-DD, 미지정 시 전체)
    - to: 조회 종료일 (YYYY-MM-DD, 미지정 시 전체)

    응답 예시:
    [
      {"date": "2026-03-28", "close_price": 2650.5},
      ...
    ]
    """
    if index_code not in _VALID_INDEX_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 지수 코드입니다. 지원 코드: {', '.join(sorted(_VALID_INDEX_CODES))}",
        )

    query = (
        select(IndexSnapshot)
        .where(IndexSnapshot.index_code == index_code)
        .order_by(IndexSnapshot.timestamp)
    )

    if from_date is not None:
        query = query.where(IndexSnapshot.timestamp >= from_date)
    if to_date is not None:
        query = query.where(IndexSnapshot.timestamp <= to_date)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    # Deduplicate by date (take the last snapshot per calendar day)
    seen_dates: dict[str, dict] = {}
    for snap in snapshots:
        day_str = snap.timestamp.date().isoformat()
        seen_dates[day_str] = {
            "date": day_str,
            "close_price": float(snap.close_price),
        }

    return list(seen_dates.values())
