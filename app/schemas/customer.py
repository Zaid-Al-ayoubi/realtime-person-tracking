from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class CustomerCreate(BaseModel):
    display_name: str | None = Field(default=None, max_length=256)


class CustomerUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=256)


class CustomerRead(TimestampedRead):
    display_name: str | None
    visit_count: int
    first_seen_at: datetime | None
    last_seen_at: datetime | None
