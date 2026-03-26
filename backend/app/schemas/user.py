# User schemas — profile read/update.
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserMe(BaseModel):
    """Response schema for the current user's profile."""

    id: int
    email: EmailStr
    name: Optional[str] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Request schema for updating the current user's profile (name only)."""

    name: Optional[str] = None
