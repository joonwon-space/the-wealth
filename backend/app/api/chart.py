"""Stock chart data API — KIS daily OHLCV for candlestick charts."""

import logging
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.kis_account import KisAccount
from app.models.user import User
from app.services.kis_token import get_kis_access_token

router = APIRouter(prefix="/chart", tags=["chart"])
logger = logging.getLogger(__name__)


@router.get("/daily")
async def get_daily_chart(
    ticker: str = Query(..., min_length=1, max_length=20),
    period: str = Query(default="3M", regex="^(1M|3M|6M|1Y|3Y)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch daily OHLCV data from KIS API for candlestick chart."""
    # Get first available KIS account
    result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id).limit(1)
    )
    acct = result.scalar_one_or_none()
    if not acct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No KIS account configured",
        )

    app_key = decrypt(acct.app_key_enc)
    app_secret = decrypt(acct.app_secret_enc)
    token = await get_kis_access_token(app_key, app_secret)

    # Calculate date range
    today = date.today()
    period_map = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 1095}
    start_date = today - timedelta(days=period_map[period])

    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST01010400",
        "Content-Type": "application/json; charset=utf-8",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ticker,
        "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
        "FID_INPUT_DATE_2": today.strftime("%Y%m%d"),
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        output2 = data.get("output2", [])
        candles = []
        for item in reversed(output2):
            dt = item.get("stck_bsop_date", "")
            if not dt or len(dt) != 8:
                continue
            candles.append(
                {
                    "time": f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}",
                    "open": float(item.get("stck_oprc", 0)),
                    "high": float(item.get("stck_hgpr", 0)),
                    "low": float(item.get("stck_lwpr", 0)),
                    "close": float(item.get("stck_clpr", 0)),
                    "volume": int(item.get("acml_vol", 0)),
                }
            )

        return {"ticker": ticker, "period": period, "candles": candles}
    except httpx.HTTPStatusError as exc:
        logger.warning("Chart data fetch failed for %s: %s", ticker, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch chart data",
        ) from exc
