import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.incident import IncidentType, IncidentSeverity, IncidentStatus


class IncidentBase(BaseModel):
    camera_id: Optional[uuid.UUID] = None
    incident_type: IncidentType
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    occurred_at: datetime
    confidence: Optional[float] = None
    notes: Optional[str] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    severity: Optional[IncidentSeverity] = None
    notes: Optional[str] = None
    video_clip_path: Optional[str] = None
    video_pre_event_path: Optional[str] = None


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: IncidentStatus
    video_clip_path: Optional[str] = None
    video_pre_event_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
