# User schemas — profile read/update.
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserMe(BaseModel):
    """Response schema for the current user's profile."""

    id: int
    email: EmailStr
    name: Optional[str] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Request schema for updating the current user's profile (name only)."""

    name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """Request schema for changing the current user's password."""

    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


class ChangeEmailRequest(BaseModel):
    """Request schema for changing the current user's email."""

    new_email: EmailStr
    current_password: str


class DeleteAccountRequest(BaseModel):
    """Request schema for deleting the current user's account."""

    current_password: str = Field(max_length=128)
