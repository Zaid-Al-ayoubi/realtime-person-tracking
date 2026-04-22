from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class CameraCreate(BaseModel):
    name: str = Field(..., max_length=128)
    source: str
    location: str | None = Field(default=None, max_length=256)
    is_active: bool = True


class CameraUpdate(BaseModel):
    name: str | None = None
    source: str | None = None
    location: str | None = None
    is_active: bool | None = None


class CameraRead(TimestampedRead):
    name: str
    source: str
    location: str | None
    is_active: bool
