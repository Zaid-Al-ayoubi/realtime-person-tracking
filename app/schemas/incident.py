from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.incident import IncidentSeverity, IncidentStatus, IncidentType
from app.schemas.common import TimestampedRead


class IncidentCreate(BaseModel):
    camera_id: uuid.UUID
    type: IncidentType
    severity: IncidentSeverity = IncidentSeverity.medium
    detected_at: datetime
    confidence: float | None = None
    notes: str | None = None


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    notes: str | None = None
    clip_path: str | None = None


class IncidentRead(TimestampedRead):
    camera_id: uuid.UUID
    type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    detected_at: datetime
    confidence: float | None
    clip_path: str | None
    notes: str | None
