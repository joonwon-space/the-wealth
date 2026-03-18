"""관심 종목 API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.models.watchlist import Watchlist

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = get_logger(__name__)


class WatchlistCreate(BaseModel):
    ticker: str
    name: str = ""
    market: str = "KRX"

    @field_validator("ticker")
    @classmethod
    def ticker_nonempty(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("ticker must not be empty")
        return v

    @field_validator("market")
    @classmethod
    def market_valid(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in {"KRX", "NYSE", "NASDAQ", "AMEX"}:
            raise ValueError("market must be one of: KRX, NYSE, NASDAQ, AMEX")
        return v


class WatchlistOut(BaseModel):
    id: int
    ticker: str
    name: str
    market: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[WatchlistOut])
async def list_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Watchlist]:
    result = await db.execute(
        select(Watchlist)
        .where(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.added_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=WatchlistOut, status_code=201)
async def add_to_watchlist(
    body: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Watchlist:
    item = Watchlist(
        user_id=current_user.id,
        ticker=body.ticker,
        name=body.name,
        market=body.market,
    )
    db.add(item)
    try:
        await db.commit()
        await db.refresh(item)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="이미 관심 종목에 추가된 종목입니다")
    return item


@router.delete("/{item_id}", status_code=204)
async def remove_from_watchlist(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.id == item_id, Watchlist.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="관심 종목을 찾을 수 없습니다")
    await db.delete(item)
    await db.commit()
