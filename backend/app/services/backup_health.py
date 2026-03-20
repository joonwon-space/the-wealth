"""Backup health helpers.

Reads the last successful backup timestamp from two sources:
1. Filesystem: scan BACKUP_DIR/daily/ for the newest .dump file mtime.
2. DB fallback: query sync_logs for the latest db_backup record.

Returns None if neither source is available (graceful degradation).
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.sync_log import SyncLog

logger = get_logger(__name__)

_BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backups")


def _read_latest_backup_mtime() -> Optional[datetime]:
    """Return the mtime of the newest .dump file in BACKUP_DIR/daily/.

    Returns None if the directory does not exist or is unreadable.
    """
    daily_dir = Path(_BACKUP_DIR) / "daily"
    try:
        dumps = list(daily_dir.glob("*.dump"))
    except (PermissionError, OSError):
        return None

    if not dumps:
        return None

    newest = max(dumps, key=lambda p: p.stat().st_mtime)
    mtime_ts = newest.stat().st_mtime
    return datetime.fromtimestamp(mtime_ts, tz=timezone.utc)


async def _read_latest_backup_from_db(db: AsyncSession) -> Optional[datetime]:
    """Return synced_at of the latest successful db_backup sync_log entry."""
    try:
        result = await db.execute(
            select(SyncLog.synced_at)
            .where(SyncLog.sync_type == "db_backup", SyncLog.status == "success")
            .order_by(SyncLog.synced_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row
    except Exception as exc:
        logger.warning("Failed to query backup status from DB: %s", exc)
        return None


async def get_last_backup_info(
    db: AsyncSession,
) -> dict:
    """Return last_backup_at and backup_age_hours for the health response.

    Tries filesystem first, then DB. Returns nulls if unavailable.

    Example return value:
    {"last_backup_at": "2026-03-20T02:00:00+00:00", "backup_age_hours": 7.5}
    """
    last_backup_at: Optional[datetime] = _read_latest_backup_mtime()

    if last_backup_at is None:
        last_backup_at = await _read_latest_backup_from_db(db)

    if last_backup_at is None:
        return {"last_backup_at": None, "backup_age_hours": None}

    now = datetime.now(tz=timezone.utc)
    age_seconds = (now - last_backup_at).total_seconds()
    age_hours = round(age_seconds / 3600, 2)

    return {
        "last_backup_at": last_backup_at.isoformat(),
        "backup_age_hours": age_hours,
    }
