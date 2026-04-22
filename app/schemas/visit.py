import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.visit import PersonType


class VisitBase(BaseModel):
    person_type: PersonType
    camera_id: Optional[uuid.UUID] = None
    entry_time: datetime
    visit_date: date
    track_id: Optional[str] = None
    session_id: Optional[str] = None


class VisitCreate(VisitBase):
    employee_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None


class VisitClose(BaseModel):
    """Payload to close/finalise an open visit."""
    exit_time: datetime


class VisitRead(VisitBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
    exit_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime


class VisitSummary(BaseModel):
    """Lightweight view used in list endpoints."""
    id: uuid.UUID
    person_type: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    visit_date: date
    employee_id: Optional[uuid.UUID] = None
    customer_id: Optional[uuid.UUID] = None
