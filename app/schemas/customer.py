import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CustomerBase(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    is_recurring: Optional[bool] = None
    notes: Optional[str] = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_count: int
    is_recurring: bool
    face_image_path: Optional[str] = None
    has_face_embedding: bool = False
    created_at: datetime
    updated_at: datetime


class CustomerReadWithStats(CustomerRead):
    """Extended read with analytics."""
    last_visit_date: Optional[datetime] = None
    avg_stay_minutes: Optional[float] = None
