"""KIS 종목 검색 프록시 엔드포인트."""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.kis_token import get_kis_access_token

router = APIRouter(prefix="/stocks", tags=["stocks"])
logger = logging.getLogger(__name__)


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="종목명 또는 티커"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """KIS 국내주식 종목 검색 프록시.

    NOTE: KIS API 자격증명이 없는 경우 빈 결과를 반환합니다.
    사용자별 KIS 키가 구현되면 current_user의 암호화된 키를 사용합니다.
    현재는 환경변수 KIS_APP_KEY/KIS_APP_SECRET을 사용합니다.
    """
    app_key = settings.KIS_APP_KEY
    app_secret = settings.KIS_APP_SECRET

    if not app_key or not app_secret:
        return {"items": [], "message": "KIS credentials not configured"}

    try:
        token = await get_kis_access_token(app_key, app_secret)
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "CTPF1002R",
            "Content-Type": "application/json; charset=utf-8",
        }
        params = {
            "prdt_type_cd": "300",
            "prdt_name": q,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/search-stock-info",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            output: Optional[list] = data.get("output")
            items = output if isinstance(output, list) else []
            return {"items": items}
    except Exception as e:
        logger.warning("KIS stock search failed: %s", e)
        return {"items": [], "message": str(e)}
