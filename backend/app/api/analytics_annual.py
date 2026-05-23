"""연간 수익률 / 은퇴 시뮬레이션 API.

- GET  /analytics/annual-returns       : 연도별 IRR/평가/적립/배당 집계.
- POST /analytics/retirement-simulation: 은퇴 시뮬레이션 순계산.
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._etag import etag_response
from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnnualReturn,
    SimulationInput,
    SimulationPoint,
)
from app.services.analytics_utils import (
    ANALYTICS_CACHE_TTL,
    analytics_key,
    get_analytics_cache,
)
from app.services.annual_returns import (
    compute_annual_returns,
    simulate_retirement,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)


@router.get("/annual-returns", response_model=list[AnnualReturn])
@limiter.limit("30/minute")
async def get_annual_returns(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FastAPIResponse:
    """사용자의 연도별 자본흐름/평가/IRR 리스트.

    캐시: Redis `analytics:{user_id}:annual-returns`, TTL 1 시간.
    sync 성공 시 `invalidate_analytics_cache` 가 자동 무효화.
    """
    cache = get_analytics_cache()
    cache_key = analytics_key(current_user.id, "annual-returns")
    cached = await cache.get(cache_key)
    if cached:
        return etag_response(request, json.loads(cached))

    rows = await compute_annual_returns(db, current_user.id, current_user.birth_year)
    await cache.setex(cache_key, ANALYTICS_CACHE_TTL, json.dumps(rows))
    return etag_response(request, rows)


@router.post(
    "/retirement-simulation",
    response_model=list[SimulationPoint],
)
@limiter.limit("60/minute")
async def post_retirement_simulation(
    request: Request,
    payload: SimulationInput,
    current_user: User = Depends(get_current_user),
) -> list[SimulationPoint]:
    """은퇴 시뮬레이션 — 매년 ``eop = bop * (1+rate) + flow``.

    DB / 캐시 무관. 입력값은 Pydantic 으로 검증.
    """
    if payload.end_age < payload.current_age:
        # 종료 나이가 현재보다 작으면 빈 리스트.
        return []
    points = simulate_retirement(payload.model_dump())
    return [SimulationPoint(**p) for p in points]
