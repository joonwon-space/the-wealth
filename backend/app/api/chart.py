"""Stock chart data API — KIS daily OHLCV for candlestick charts."""

from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.core.encryption import decrypt
from app.db.session import get_db
from app.models.kis_account import KisAccount
from app.models.user import User
from app.services.kis_token import get_kis_access_token

router = APIRouter(prefix="/chart", tags=["chart"])
logger = get_logger(__name__)


@router.get("/daily")
async def get_daily_chart(
    ticker: str = Query(..., min_length=1, max_length=20),
    period: str = Query(default="3M", pattern="^(1M|3M|6M|1Y|3Y)$"),
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

    # Calculate date range + KIS period code
    # KIS returns max 100 items per call, so use weekly/monthly for longer periods
    today = date.today()
    period_config = {
        "1M": (30, "D"),
        "3M": (90, "D"),
        "6M": (180, "W"),
        "1Y": (365, "W"),
        "3Y": (1095, "M"),
    }
    days_back, kis_period = period_config[period]
    start_date = today - timedelta(days=days_back)

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
        "FID_PERIOD_DIV_CODE": kis_period,
        "FID_ORG_ADJ_PRC": "0",
    }

    try:
        all_items: list[dict] = []
        current_end = today
        max_pages = 10  # safety limit

        async with httpx.AsyncClient(timeout=10.0) as client:
            for _ in range(max_pages):
                params["FID_INPUT_DATE_2"] = current_end.strftime("%Y%m%d")
                resp = await client.get(
                    f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

                items = (
                    data.get("output")
                    or data.get("output2")
                    or data.get("output1")
                    or []
                )
                if not items:
                    break

                all_items.extend(items)

                # KIS returns max 100 items; fewer means no more data
                if len(items) < 100:
                    break

                # Last item is the oldest date in this batch
                oldest = items[-1].get("stck_bsop_date", "")
                if not oldest or oldest <= start_date.strftime("%Y%m%d"):
                    break

                # Next page: end 1 day before oldest
                from datetime import datetime as dt_cls

                oldest_date = dt_cls.strptime(oldest, "%Y%m%d").date()
                current_end = oldest_date - timedelta(days=1)
                if current_end < start_date:
                    break

        # Deduplicate by date and sort ascending
        seen: set[str] = set()
        candles = []
        for item in reversed(all_items):
            d = item.get("stck_bsop_date", "")
            if not d or len(d) != 8 or d in seen:
                continue
            if d < start_date.strftime("%Y%m%d"):
                continue
            seen.add(d)
            candles.append(
                {
                    "time": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
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
