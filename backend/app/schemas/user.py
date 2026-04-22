# User schemas — profile read/update.
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserMe(BaseModel):
    """Response schema for the current user's profile."""

    id: int
    email: EmailStr
    name: Optional[str] = None
    strategy_tag: str = "mixed"
    long_short_ratio: int = 70

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Request schema for updating the current user's profile.

    `name` 은 표시 이름. `strategy_tag` + `long_short_ratio` 는 Dual-brain 설정.
    """

    name: Optional[str] = Field(None, max_length=100)
    strategy_tag: Optional[str] = Field(
        default=None,
        pattern="^(long|short|mixed)$",
    )
    long_short_ratio: Optional[int] = Field(default=None, ge=0, le=100)


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
