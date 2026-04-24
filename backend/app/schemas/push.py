from typing import Optional

from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=64)


class PushSubscriptionCreate(BaseModel):
    """Payload posted from the client after PushManager.subscribe()."""

    endpoint: str = Field(min_length=1, max_length=500)
    keys: PushKeys
    user_agent: Optional[str] = Field(default=None, max_length=255)


class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    user_agent: Optional[str] = None

    model_config = {"from_attributes": True}


class PushPublicKeyResponse(BaseModel):
    public_key: str
    enabled: bool
