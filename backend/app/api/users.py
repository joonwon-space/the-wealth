"""User API — KIS credentials and account management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import decrypt, encrypt
from app.core.limiter import limiter
from app.core.security import (
    hash_password,
    revoke_all_refresh_tokens_for_user,
    verify_password,
)
from app.db.session import get_db
from app.models.kis_account import KisAccount
from app.models.portfolio import Portfolio
from app.models.security_audit_log import AuditAction, SecurityAuditLog
from app.models.user import User
from app.schemas.user import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    DeleteAccountRequest,
    UserMe,
    UserUpdate,
)
from app.services.audit_service import log_event
from app.services.kis_token import get_kis_access_token

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMe)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the current user's profile (email and name)."""
    return current_user


@router.patch("/me", response_model=UserMe)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update the current user's display name and/or Dual-brain strategy."""
    if body.name is not None:
        current_user.name = body.name or None
    if body.strategy_tag is not None:
        current_user.strategy_tag = body.strategy_tag
    if body.long_short_ratio is not None:
        current_user.long_short_ratio = body.long_short_ratio
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=200)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the current user's password.

    Verifies the current password, updates the hash, and invalidates all
    existing refresh tokens to force re-authentication.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    await revoke_all_refresh_tokens_for_user(current_user.id)
    return {"message": "Password changed successfully"}


@router.post("/me/change-email", status_code=200)
@limiter.limit("5/minute")
async def change_email(
    request: Request,
    body: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the current user's email address.

    Requires the current password for verification. Fails if the new email is
    already taken. Invalidates all refresh tokens on success.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    existing = await db.execute(
        select(User).where(User.email == str(body.new_email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )
    current_user.email = str(body.new_email)
    await db.commit()
    await revoke_all_refresh_tokens_for_user(current_user.id)
    return {"message": "Email changed successfully"}


@router.delete("/me", status_code=200)
@limiter.limit("5/minute")
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Permanently delete the current user's account.

    Requires the current password for confirmation. Cascades to delete all
    portfolios, holdings, transactions, orders, alerts, notifications,
    KIS accounts, and watchlist entries. Invalidates all Redis tokens.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user_id = current_user.id
    await log_event(db, AuditAction.ACCOUNT_DELETE, user_id=user_id, request=request)
    await db.delete(current_user)
    await db.commit()
    await revoke_all_refresh_tokens_for_user(user_id)
    return {"message": "Account deleted successfully"}


class KisAccountCreate(BaseModel):
    label: str = Field(max_length=100)
    account_no: str = Field(max_length=20)
    acnt_prdt_cd: str = "01"
    app_key: str
    app_secret: str
    is_paper_trading: bool = False
    account_type: str = Field(default="일반", max_length=50)  # 일반, ISA, 연금저축, IRP, 해외주식


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
        is_paper_trading=body.is_paper_trading,
        account_type=body.account_type or None,
    )
    db.add(acct)
    await log_event(
        db,
        AuditAction.KIS_CREDENTIAL_ADD,
        user_id=current_user.id,
        meta={"account_no": body.account_no, "label": body.label},
    )
    await db.commit()
    await db.refresh(acct)
    return {
        "id": acct.id,
        "label": acct.label,
        "account_no": acct.account_no,
        "acnt_prdt_cd": acct.acnt_prdt_cd,
        "is_paper_trading": acct.is_paper_trading,
        "account_type": acct.account_type,
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
            "is_paper_trading": a.is_paper_trading,
            "account_type": a.account_type,
        }
        for a in result.scalars().all()
    ]


class KisAccountUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=100)
    is_paper_trading: Optional[bool] = None
    account_type: Optional[str] = Field(None, max_length=50)


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
    if body.label is not None:
        acct.label = body.label
        # Also update linked portfolio name
        port_result = await db.execute(
            select(Portfolio).where(Portfolio.kis_account_id == acct.id)
        )
        portfolio = port_result.scalar_one_or_none()
        if portfolio:
            portfolio.name = body.label

    if body.is_paper_trading is not None:
        acct.is_paper_trading = body.is_paper_trading

    if body.account_type is not None:
        acct.account_type = body.account_type or None

    await db.commit()
    return {
        "id": acct.id,
        "label": acct.label,
        "account_no": acct.account_no,
        "acnt_prdt_cd": acct.acnt_prdt_cd,
        "is_paper_trading": acct.is_paper_trading,
        "account_type": acct.account_type,
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
    await log_event(
        db,
        AuditAction.KIS_CREDENTIAL_DELETE,
        user_id=current_user.id,
        meta={"account_no": acct.account_no, "label": acct.label},
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


@router.get("/me/security-logs")
async def get_security_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the 50 most recent security audit log entries for the current user."""
    result = await db.execute(
        select(SecurityAuditLog)
        .where(SecurityAuditLog.user_id == current_user.id)
        .order_by(SecurityAuditLog.created_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action.value,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
            "meta": log.meta,
        }
        for log in logs
    ]
