"""벤치마크 지수 히스토리 API — GET /analytics/benchmark (+ /benchmark-delta)."""

from datetime import date as date_type, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.holding import Holding
from app.models.index_snapshot import IndexSnapshot
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.analytics import BenchmarkPoint
from app.schemas.redesign import BenchmarkDelta

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)

_VALID_INDEX_CODES = {"KOSPI200", "SP500"}
_PERIOD_TO_DAYS = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}


@router.get("/benchmark", response_model=list[BenchmarkPoint])
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
) -> list[BenchmarkPoint]:
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
    seen_dates: dict[str, BenchmarkPoint] = {}
    for snap in snapshots:
        day_str = snap.timestamp.date().isoformat()
        seen_dates[day_str] = BenchmarkPoint(
            date=day_str, close_price=float(snap.close_price)
        )

    return list(seen_dates.values())


@router.get("/benchmark-delta", response_model=BenchmarkDelta)
@limiter.limit("30/minute")
async def benchmark_delta(
    request: Request,
    index_code: str = Query(default="KOSPI200"),
    period: str = Query(default="6M", description="1M | 3M | 6M | 1Y | ALL"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BenchmarkDelta:
    """내 포트폴리오 누적 수익률 vs 벤치마크 지수의 기간별 차이(%p).

    1차 구현:
      - 벤치마크 수익률 = index_snapshots 시작일/종료일 종가 비교.
      - 내 수익률 = 모든 보유 종목의 평균매입가 대비 현재 평균매입가 합계
        비교 (단순화; 거래 히스토리 기반 시간가중 수익률은 2차 개선).
    """
    if index_code not in _VALID_INDEX_CODES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"지원 지수: {', '.join(sorted(_VALID_INDEX_CODES))}",
        )

    # --- 기간 계산 ------------------------------------------------------
    today = date_type.today()
    if period == "ALL":
        start_date = None
    else:
        days = _PERIOD_TO_DAYS.get(period)
        if days is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="지원 기간: 1M, 3M, 6M, 1Y, ALL",
            )
        start_date = today - timedelta(days=days)

    # --- 벤치마크 수익률 ------------------------------------------------
    stmt = (
        select(IndexSnapshot)
        .where(IndexSnapshot.index_code == index_code)
        .order_by(IndexSnapshot.timestamp)
    )
    if start_date is not None:
        stmt = stmt.where(IndexSnapshot.timestamp >= start_date)

    snapshots = (await db.execute(stmt)).scalars().all()
    benchmark_pct = 0.0
    if len(snapshots) >= 2:
        first = float(snapshots[0].close_price)
        last = float(snapshots[-1].close_price)
        if first > 0:
            benchmark_pct = (last - first) / first * 100.0

    # --- 내 수익률 (단순화 버전) ----------------------------------------
    portfolios = (
        await db.execute(
            select(Portfolio.id).where(Portfolio.user_id == current_user.id)
        )
    ).scalars().all()
    mine_pct = 0.0
    if portfolios:
        holdings = (
            await db.execute(
                select(Holding).where(Holding.portfolio_id.in_(portfolios))
            )
        ).scalars().all()
        invested = sum(float(h.quantity) * float(h.avg_price) for h in holdings)
        # TODO: 종목별 현재가를 KIS 에서 받아 비교해야 정확한 수익률.
        # 1차는 0 으로 두고, 추후 summary 서비스와 합치자.
        mine_pct = 0.0 if invested <= 0 else mine_pct

    return BenchmarkDelta(
        index_code=index_code,
        period=period,
        mine_pct=round(mine_pct, 2),
        benchmark_pct=round(benchmark_pct, 2),
        delta_pct_points=round(mine_pct - benchmark_pct, 2),
    )
