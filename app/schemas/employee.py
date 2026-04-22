from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.employee import EmployeeStatus
from app.schemas.common import TimestampedRead


class EmployeeCreate(BaseModel):
    full_name: str = Field(..., max_length=256)
    role: str | None = Field(default=None, max_length=128)
    external_ref: str | None = Field(default=None, max_length=128)
    status: EmployeeStatus = EmployeeStatus.active


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    external_ref: str | None = None
    status: EmployeeStatus | None = None


class EmployeeRead(TimestampedRead):
    full_name: str
    role: str | None
    external_ref: str | None
    status: EmployeeStatus
    is_enrolled: bool
