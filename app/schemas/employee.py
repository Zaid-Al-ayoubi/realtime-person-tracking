import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class EmployeeBase(BaseModel):
    name: str
    role: Optional[str] = None
    employee_code: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    employee_code: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    face_image_path: Optional[str] = None
    has_face_embedding: bool = False
    created_at: datetime
    updated_at: datetime


class EmployeeReadWithStats(EmployeeRead):
    """Extended read with today's visit stats."""
    total_visits: int = 0
    hours_today: float = 0.0
