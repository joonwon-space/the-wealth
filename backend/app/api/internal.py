"""Internal system API endpoints.

These endpoints are called by server-side scripts (e.g. backup-postgres.sh)
and are NOT exposed to the public. They are protected by a shared secret
(INTERNAL_SECRET env var) passed as the X-Internal-Secret header.

If INTERNAL_SECRET is empty the endpoints return 503.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.sync_log import SyncLog

router = APIRouter(prefix="/internal", tags=["internal"])
logger = get_logger(__name__)


def _verify_internal_secret(x_internal_secret: str = Header(default="")) -> None:
    """Dependency: verify the X-Internal-Secret header matches INTERNAL_SECRET."""
    if not settings.INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal endpoints are disabled (INTERNAL_SECRET not configured)",
        )
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal secret",
        )


class BackupStatusPayload(BaseModel):
    status: str  # "success" | "error"
    message: str = ""


@router.post(
    "/backup-status",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_verify_internal_secret)],
)
async def record_backup_status(
    payload: BackupStatusPayload,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Record a DB backup result to sync_logs.

    Called by backup-postgres.sh after each run.
    Stores a SyncLog with sync_type='db_backup', no user_id/portfolio_id.
    """
    if payload.status not in ("success", "error"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be 'success' or 'error'",
        )

    log = SyncLog(
        user_id=None,
        portfolio_id=None,
        sync_type="db_backup",
        status=payload.status,
        message=payload.message[:500] if payload.message else "",
    )
    db.add(log)
    await db.commit()

    log_fn = logger.info if payload.status == "success" else logger.error
    log_fn(
        "[Backup] Status recorded: status=%s message=%s",
        payload.status,
        payload.message[:200] if payload.message else "",
    )
