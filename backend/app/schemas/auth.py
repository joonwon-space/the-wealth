from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    # max_length=128 prevents bcrypt DoS (bcrypt truncates at 72 bytes; 128 chars
    # is a safe upper bound that rejects absurdly long passwords before hashing).
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # refresh_token optional — can come from HttpOnly cookie instead
    refresh_token: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
