"""User API — KIS credentials and account management."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt, encrypt
from app.db.session import get_db
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.user import KisCredentialsRequest
from app.services.kis_token import get_kis_access_token

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/kis-credentials", status_code=204)
async def save_kis_credentials(
    body: KisCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Save KIS credentials to user model (legacy)."""
    current_user.kis_app_key_enc = encrypt(body.app_key)
    current_user.kis_app_secret_enc = encrypt(body.app_secret)
    if body.account_no:
        current_user.kis_account_no = body.account_no
        current_user.kis_acnt_prdt_cd = body.acnt_prdt_cd
    await db.commit()


class KisAccountCreate(BaseModel):
    label: str
    account_no: str
    acnt_prdt_cd: str = "01"
    app_key: str
    app_secret: str


@router.post("/kis-accounts", status_code=201)
async def add_kis_account(
    body: KisAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new KIS account (encrypted)."""
    # Check duplicate
    existing = await db.execute(
        select(KisAccount).where(
            KisAccount.user_id == current_user.id,
            KisAccount.account_no == body.account_no,
            KisAccount.acnt_prdt_cd == body.acnt_prdt_cd,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already registered"
        )

    acct = KisAccount(
        user_id=current_user.id,
        label=body.label,
        account_no=body.account_no,
        acnt_prdt_cd=body.acnt_prdt_cd,
        app_key_enc=encrypt(body.app_key),
        app_secret_enc=encrypt(body.app_secret),
    )
    db.add(acct)
    await db.commit()
    await db.refresh(acct)
    return {
        "id": acct.id,
        "label": acct.label,
        "account_no": acct.account_no,
        "acnt_prdt_cd": acct.acnt_prdt_cd,
    }


@router.get("/kis-accounts")
async def list_kis_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all KIS accounts for the current user (no secrets returned)."""
    result = await db.execute(
        select(KisAccount).where(KisAccount.user_id == current_user.id)
    )
    return [
        {
            "id": a.id,
            "label": a.label,
            "account_no": a.account_no,
            "acnt_prdt_cd": a.acnt_prdt_cd,
        }
        for a in result.scalars().all()
    ]


class KisAccountUpdate(BaseModel):
    label: str


@router.patch("/kis-accounts/{account_id}")
async def update_kis_account(
    account_id: int,
    body: KisAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update KIS account label."""
    acct = await db.get(KisAccount, account_id)
    if not acct or acct.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="KIS account not found"
        )
    acct.label = body.label

    # Also update linked portfolio name
    port_result = await db.execute(
        select(Portfolio).where(Portfolio.kis_account_id == acct.id)
    )
    portfolio = port_result.scalar_one_or_none()
    if portfolio:
        portfolio.name = body.label

    await db.commit()
    return {
        "id": acct.id,
        "label": acct.label,
        "account_no": acct.account_no,
        "acnt_prdt_cd": acct.acnt_prdt_cd,
    }


@router.delete("/kis-accounts/{account_id}", status_code=204)
async def delete_kis_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a KIS account."""
    acct = await db.get(KisAccount, account_id)
    if not acct or acct.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="KIS account not found"
        )
    await db.delete(acct)
    await db.commit()


@router.post("/kis-accounts/{account_id}/test")
async def test_kis_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Test KIS account connectivity by attempting token issuance."""
    acct = await db.get(KisAccount, account_id)
    if not acct or acct.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="KIS account not found"
        )
    try:
        app_key = decrypt(acct.app_key_enc)
        app_secret = decrypt(acct.app_secret_enc)
        await get_kis_access_token(app_key, app_secret)
        return {"success": True, "message": "KIS API 연결 성공"}
    except Exception:
        return {"success": False, "message": "KIS API 연결 실패 — 자격증명을 확인해주세요"}
