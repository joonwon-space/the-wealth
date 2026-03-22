"""Pydantic schemas for the notifications API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    """Response schema for a single notification record."""

    id: int
    user_id: int
    type: str
    title: str
    body: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
