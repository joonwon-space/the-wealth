"""Web Push subscription management.

Endpoints:
  GET    /push/public-key        - return VAPID public key + enabled flag
  POST   /push/subscribe         - register device subscription (upsert by endpoint)
  DELETE /push/subscribe         - remove a subscription by endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.schemas.push import (
    PushPublicKeyResponse,
    PushSubscriptionCreate,
    PushSubscriptionResponse,
)
from app.services.push_sender import push_enabled

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/public-key", response_model=PushPublicKeyResponse)
@limiter.limit("30/minute")
async def get_public_key(request: Request) -> PushPublicKeyResponse:
    return PushPublicKeyResponse(
        public_key=settings.VAPID_PUBLIC_KEY,
        enabled=push_enabled(),
    )


@router.post(
    "/subscribe",
    response_model=PushSubscriptionResponse,
    status_code=201,
)
@limiter.limit("10/minute")
async def subscribe(
    request: Request,
    payload: PushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushSubscription:
    """Create or update a push subscription for the current user.

    Uniqueness is enforced on `endpoint`; reposting from the same device
    simply refreshes the keys and user_agent rather than creating duplicates.
    """
    existing = (
        await db.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == payload.endpoint
            )
        )
    ).scalar_one_or_none()

    if existing:
        # Re-bind to the current user (e.g. same browser, different account)
        # and refresh the keys.
        existing.user_id = current_user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        existing.user_agent = payload.user_agent
        await db.commit()
        await db.refresh(existing)
        return existing

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
        user_agent=payload.user_agent,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.delete("/subscribe", status_code=204)
@limiter.limit("10/minute")
async def unsubscribe(
    request: Request,
    endpoint: str = Query(..., min_length=1, max_length=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a subscription owned by the current user (by endpoint)."""
    result = await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == current_user.id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="subscription not found")
    await db.commit()
