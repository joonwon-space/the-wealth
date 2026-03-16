"""종목 검색 엔드포인트 — KRX 상장 종목 로컬 검색."""
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
    q: str = Query(..., min_length=1, description="종목명 또는 티커"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """KRX 상장 종목 로컬 검색 (KOSPI + KOSDAQ).

    첫 요청 시 KRX에서 전체 종목 리스트를 받아 Redis에 24시간 캐싱.
    """
    try:
        items = await _search(q)
        return {"items": items}
    except Exception as e:
        logger.warning("Stock search failed: %s", e)
        return {"items": [], "message": str(e)}
