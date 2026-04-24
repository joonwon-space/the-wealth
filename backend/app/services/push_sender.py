"""Web Push delivery using VAPID.

Wraps `pywebpush` with async-safe helpers. The library itself is synchronous
(requests under the hood) so each send runs in a thread to avoid blocking
the FastAPI event loop. Subscriptions that return 404/410 are pruned from the
database automatically.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PushPayload:
    title: str
    body: str
    url: str = "/dashboard"
    tag: Optional[str] = None


def push_enabled() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def _send_one(subscription_info: dict, payload: PushPayload) -> int:
    """Sync call — returns HTTP status. Raises on network-level errors."""
    # Import lazily so the module is importable even when pywebpush isn't yet
    # installed (e.g. fresh checkout without `pip install -r requirements.txt`).
    from pywebpush import WebPushException, webpush

    try:
        response = webpush(
            subscription_info=subscription_info,
            data=json.dumps(
                {
                    "title": payload.title,
                    "body": payload.body,
                    "url": payload.url,
                    "tag": payload.tag,
                }
            ),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            timeout=10,
        )
        return response.status_code
    except WebPushException as exc:  # noqa: BLE001 — library raises a broad type
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        if status is not None:
            return int(status)
        raise


async def send_push(
    db: AsyncSession,
    user_id: int,
    payload: PushPayload,
) -> int:
    """Deliver `payload` to every subscription for `user_id`.

    Returns the number of successful sends. Silently returns 0 when VAPID
    keys aren't configured — callers can rely on it as a no-op fallback.
    """
    if not push_enabled():
        return 0

    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    subs = result.scalars().all()
    if not subs:
        return 0

    loop = asyncio.get_running_loop()
    tasks = [
        loop.run_in_executor(
            None,
            _send_one,
            {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            payload,
        )
        for sub in subs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    stale_ids: list[int] = []
    success = 0
    for sub, outcome in zip(subs, results, strict=True):
        if isinstance(outcome, Exception):
            logger.warning("push send failed for sub %s: %s", sub.id, outcome)
            continue
        status = int(outcome)
        if status in (404, 410):
            stale_ids.append(sub.id)
        elif 200 <= status < 300:
            success += 1
        else:
            logger.warning("push send status=%s sub=%s", status, sub.id)

    if stale_ids:
        await db.execute(
            delete(PushSubscription).where(PushSubscription.id.in_(stale_ids))
        )
        await db.commit()
        logger.info("pruned %d stale push subscriptions", len(stale_ids))

    return success
