"""종목 검색 엔드포인트 — KIS 마스터 파일 기반 로컬 검색."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.services.stock_search import search_stocks as _search

router = APIRouter(prefix="/stocks", tags=["stocks"])
logger = logging.getLogger(__name__)


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, max_length=50, description="종목명 또는 티커"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """KIS 마스터 파일 기반 종목 검색 (국내 + 해외)."""
    try:
        items = await _search(q)
        return {"items": items}
    except Exception as e:
        logger.warning("Stock search failed: %s", e)
        return {"items": [], "message": "검색을 일시적으로 사용할 수 없습니다."}
