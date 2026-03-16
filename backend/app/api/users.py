"""사용자 관련 API — KIS 자격증명 저장 등."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import encrypt
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import KisCredentialsRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/kis-credentials", status_code=204)
async def save_kis_credentials(
    body: KisCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """KIS API 자격증명을 AES-256-GCM으로 암호화하여 저장."""
    current_user.kis_app_key_enc = encrypt(body.app_key)
    current_user.kis_app_secret_enc = encrypt(body.app_secret)
    await db.commit()
