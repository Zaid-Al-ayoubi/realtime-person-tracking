import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CameraBase(BaseModel):
    name: str
    source: str
    location: Optional[str] = None
    branch: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    location: Optional[str] = None
    branch: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CameraRead(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
