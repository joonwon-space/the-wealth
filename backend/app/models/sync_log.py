from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    portfolio_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    # sync_type distinguishes portfolio sync events from system-level events.
    # Values: 'portfolio' (default) | 'db_backup'
    sync_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="portfolio"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | error
    inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
