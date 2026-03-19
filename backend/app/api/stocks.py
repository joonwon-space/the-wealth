"""종목 검색 엔드포인트 — KIS 마스터 파일 기반 로컬 검색."""

import re
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.holding import Holding
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.kis_token import get_kis_access_token
from app.services.kis_price import fetch_usd_krw_rate
from app.services.stock_search import search_stocks as _search

router = APIRouter(prefix="/stocks", tags=["stocks"])
logger = get_logger(__name__)

_DOMESTIC_TICKER_RE = re.compile(r"^\d{6}$")


def _is_domestic(ticker: str) -> bool:
    return bool(_DOMESTIC_TICKER_RE.match(ticker))


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
    """종목 상세 정보 조회.

    - 국내주식(6자리 숫자): KIS FHKST01010100
    - 해외주식(그 외): KIS HHDFS00000300 (Holding.market 참조)

    Returns: ticker, name, current_price, open, high, low, prev_close,
             volume, market_cap, per, pbr, eps, bps,
             w52_high, w52_low, day_change_rate, currency
    """
    acct_result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
    )
    acct = acct_result.scalar_one_or_none()
    if not acct:
        return {"ticker": ticker, "error": "KIS 계정이 없습니다"}

    app_key = decrypt(acct.app_key_enc)
    app_secret = decrypt(acct.app_secret_enc)

    # 보유 현황 조회 (market 코드 포함)
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio_ids = [p.id for p in port_result.scalars().all()]
    my_holding: Optional[dict] = None
    holding_market: Optional[str] = None
    holding_name: Optional[str] = None
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
            holding_market = holding.market
            holding_name = holding.name

    if _is_domestic(ticker):
        return await _fetch_domestic_detail(
            ticker, app_key, app_secret, holding_name, my_holding
        )
    else:
        market = holding_market or "NAS"
        return await _fetch_overseas_detail(
            ticker, market, app_key, app_secret, holding_name, my_holding
        )


async def _fetch_domestic_detail(
    ticker: str,
    app_key: str,
    app_secret: str,
    holding_name: Optional[str],
    my_holding: Optional[dict],
) -> dict:
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
        logger.warning("Failed to fetch domestic stock detail for %s: %s", ticker, e)
        return {"ticker": ticker, "error": "가격 정보를 가져올 수 없습니다"}

    def _dec(key: str) -> Optional[float]:
        v = output.get(key, "")
        try:
            return float(v) if v and v != "0" else None
        except ValueError:
            return None

    name = output.get("hts_kor_isnm") or holding_name or ticker

    return {
        "ticker": ticker,
        "name": name,
        "currency": "KRW",
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


async def _fetch_overseas_detail(
    ticker: str,
    market: str,
    app_key: str,
    app_secret: str,
    holding_name: Optional[str],
    my_holding: Optional[dict],
) -> dict:
    try:
        token = await get_kis_access_token(app_key, app_secret)
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "HHDFS00000300",
            "Content-Type": "application/json; charset=utf-8",
        }
        params = {"AUTH": "", "EXCD": market, "SYMB": ticker}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            output = resp.json().get("output", {})
            usd_krw_rate = await fetch_usd_krw_rate(app_key, app_secret, client)
    except Exception as e:
        logger.warning("Failed to fetch overseas stock detail for %s: %s", ticker, e)
        return {"ticker": ticker, "error": "가격 정보를 가져올 수 없습니다"}

    def _dec(key: str) -> Optional[float]:
        v = output.get(key, "")
        try:
            return float(v) if v and v != "0" else None
        except ValueError:
            return None

    name = output.get("rsym") or output.get("symb") or holding_name or ticker

    return {
        "ticker": ticker,
        "name": name,
        "currency": "USD",
        "market": market,
        "usd_krw_rate": float(usd_krw_rate),
        "current_price": _dec("last"),
        "open": _dec("open"),
        "high": _dec("high"),
        "low": _dec("low"),
        "prev_close": _dec("base"),
        "volume": _dec("tvol"),
        "day_change_rate": _dec("rate"),
        "market_cap": None,
        "per": _dec("perx"),
        "pbr": _dec("pbrx"),
        "eps": _dec("epsx"),
        "bps": None,
        "w52_high": _dec("w52hgpr"),
        "w52_low": _dec("w52lwpr"),
        "my_holding": my_holding,
    }
