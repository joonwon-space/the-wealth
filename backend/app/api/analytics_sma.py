"""이동평균(SMA) API — GET /analytics/stocks/{ticker}/sma."""

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._etag import etag_response
from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.schemas.analytics import SmaPoint

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)


def _compute_sma(closes: list[float], period: int) -> list[Optional[float]]:
    """단순 이동평균 계산.

    Args:
        closes: 날짜 순으로 정렬된 종가 리스트.
        period: 이동평균 기간 (일).

    Returns:
        각 날짜의 SMA 값 리스트.  데이터가 부족한 초기 지점은 None.
    """
    result: list[Optional[float]] = []
    for i, _ in enumerate(closes):
        if i < period - 1:
            result.append(None)
        else:
            window = closes[i - period + 1 : i + 1]
            result.append(round(sum(window) / period, 4))
    return result


@router.get("/stocks/{ticker}/sma", response_model=list[SmaPoint])
@limiter.limit("30/minute")
async def get_stock_sma(
    request: Request,
    ticker: str,
    period: int = Query(
        default=20,
        ge=2,
        le=200,
        description="이동평균 기간 (일). 기본 20일. 최소 2, 최대 200.",
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
) -> FastAPIResponse:
    """종목별 단순 이동평균(SMA) 시계열 반환 (ETag/304 적용).

    price_snapshots 테이블에서 해당 ticker의 날짜별 종가를 조회하고
    지정 기간(period)의 SMA를 계산하여 반환한다.

    쿼리 파라미터:
    - period: 이동평균 기간 (기본 20일, 범위 2~200)
    - from: 조회 시작일 (YYYY-MM-DD, 미지정 시 전체)
    - to: 조회 종료일 (YYYY-MM-DD, 미지정 시 전체)

    응답 예시:
    [
      {"date": "2025-11-01", "sma": 71250.5},
      {"date": "2025-11-04", "sma": 71800.0},
      ...
    ]

    SMA 계산에 필요한 이전 데이터(최대 period-1일)를 포함해서 DB를 조회하며,
    응답에는 from 이후 날짜의 포인트만 포함된다 (from 미지정 시 전체).
    SMA 값이 None인 초기 포인트는 응답에서 제외된다.
    """
    # 이동평균 계산을 위해 from_date 이전 period-1 일치의 스냅샷도 조회
    from datetime import timedelta

    fetch_from = (
        from_date - timedelta(days=period * 2) if from_date is not None else None
    )

    query = (
        select(PriceSnapshot)
        .where(PriceSnapshot.ticker == ticker)
        .order_by(PriceSnapshot.snapshot_date)
    )

    if fetch_from is not None:
        query = query.where(PriceSnapshot.snapshot_date >= fetch_from)
    if to_date is not None:
        query = query.where(PriceSnapshot.snapshot_date <= to_date)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    if not snapshots:
        return etag_response(request, [])

    dates = [s.snapshot_date.isoformat() for s in snapshots]
    closes = [float(s.close) for s in snapshots]

    sma_values = _compute_sma(closes, period)

    # 응답: from_date 이후 날짜 + SMA 값이 있는 포인트만 포함
    output: list[SmaPoint] = []
    for date_str, sma in zip(dates, sma_values):
        if sma is None:
            continue
        if from_date is not None and date_str < from_date.isoformat():
            continue
        output.append(SmaPoint(date=date_str, sma=sma))

    return etag_response(request, [p.model_dump() for p in output])
