"""Security audit logging service.

Provides a single ``log_event`` coroutine that records sensitive user actions
to the ``security_audit_logs`` table.  Errors are swallowed so that a logging
failure never blocks the primary request.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security_audit_log import AuditAction, SecurityAuditLog

logger = logging.getLogger(__name__)


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _user_agent(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    return request.headers.get("user-agent")


async def log_event(
    db: AsyncSession,
    action: AuditAction,
    *,
    user_id: Optional[int] = None,
    request: Optional[Request] = None,
    meta: Optional[dict] = None,
) -> None:
    """Append an audit log entry.

    Args:
        db: AsyncSession for the current request.
        action: The ``AuditAction`` enum value to record.
        user_id: The authenticated user's ID (may be None for login failures).
        request: FastAPI Request object used to extract IP and user-agent.
        meta: Optional extra context stored as JSONB (e.g. ``{"email": ...}``).
    """
    try:
        entry = SecurityAuditLog(
            user_id=user_id,
            action=action,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            meta=meta,
        )
        db.add(entry)
        await db.flush()
    except Exception:
        logger.exception("Failed to write audit log entry (action=%s, user_id=%s)", action, user_id)
