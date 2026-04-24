from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PushSubscription(Base):
    """Web Push subscription for a user device/browser.

    Created when the frontend calls `POST /api/v1/push/subscribe` after the
    user grants Notification permission. Removed on `DELETE` or when a push
    send receives HTTP 410 Gone from the push service.
    """

    __tablename__ = "push_subscriptions"
    __table_args__ = (
        Index("ix_push_subscriptions_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Push service endpoint URL (unique per device/browser).
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    # Encryption keys from the browser PushSubscription object.
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
