"""알림 센터 API.

엔드포인트:
  GET  /notifications                  - 내 알림 목록 (미읽음 먼저)
  PATCH /notifications/{id}/read       - 단건 읽음 처리
  POST /notifications/read-all         - 전체 읽음 처리
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = get_logger(__name__)


@router.get("", response_model=list[NotificationOut])
@limiter.limit("60/minute")
async def list_notifications(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Notification]:
    """내 알림 목록 조회.

    - 미읽음(is_read=False) 먼저, 이후 최신순 정렬.
    - 최대 100건 반환.
    """
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.is_read.asc(), Notification.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())


@router.patch("/{notification_id}/read", response_model=NotificationOut)
@limiter.limit("60/minute")
async def mark_notification_read(
    request: Request,
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Notification:
    """단건 읽음 처리."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


@router.post("/read-all", status_code=204)
@limiter.limit("60/minute")
async def mark_all_notifications_read(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """전체 읽음 처리."""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
