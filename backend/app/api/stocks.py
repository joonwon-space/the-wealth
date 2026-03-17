"""종목 검색 엔드포인트 — KIS 마스터 파일 기반 로컬 검색."""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.kis_token import get_kis_access_token
from app.services.stock_search import search_stocks as _search
from fastapi import Query

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


@router.get("/{ticker}/detail")
async def get_stock_detail(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """종목 상세 정보 조회 — KIS FHKST01010100 (국내주식 현재가).

    Returns: ticker, current_price, open, high, low, prev_close,
             volume, market_cap, per, pbr, eps, bps,
             w52_high, w52_low, day_change_rate
    """
    acct_result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
    )
    acct = acct_result.scalar_one_or_none()
    if not acct:
        return {"ticker": ticker, "error": "KIS 계정이 없습니다"}

    app_key = decrypt(acct.app_key_enc)
    app_secret = decrypt(acct.app_secret_enc)

    try:
        token = await get_kis_access_token(app_key, app_secret)
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHKST01010100",
            "Content-Type": "application/json; charset=utf-8",
        }
        params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": ticker}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers=headers,
                params=params,
            )
        resp.raise_for_status()
        output = resp.json().get("output", {})
    except Exception as e:
        logger.warning("Failed to fetch stock detail for %s: %s", ticker, e)
        return {"ticker": ticker, "error": "가격 정보를 가져올 수 없습니다"}

    def _dec(key: str) -> Optional[float]:
        v = output.get(key, "")
        try:
            return float(v) if v and v != "0" else None
        except ValueError:
            return None

    # 보유 현황 조회
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    my_holding: Optional[dict] = None
    if portfolio_ids:
        hold_result = await db.execute(
            select(Holding).where(
                Holding.portfolio_id.in_(portfolio_ids),
                Holding.ticker == ticker,
            ).limit(1)
        )
        holding = hold_result.scalar_one_or_none()
        if holding:
            my_holding = {
                "quantity": float(holding.quantity),
                "avg_price": float(holding.avg_price),
            }

    return {
        "ticker": ticker,
        "current_price": _dec("stck_prpr"),
        "open": _dec("stck_oprc"),
        "high": _dec("stck_hgpr"),
        "low": _dec("stck_lwpr"),
        "prev_close": _dec("stck_sdpr"),
        "volume": _dec("acml_vol"),
        "day_change_rate": _dec("prdy_ctrt"),
        "market_cap": _dec("hts_avls"),  # 억원
        "per": _dec("per"),
        "pbr": _dec("pbr"),
        "eps": _dec("eps"),
        "bps": _dec("bps"),
        "w52_high": _dec("w52_hgpr"),
        "w52_low": _dec("w52_lwpr"),
        "my_holding": my_holding,
    }
