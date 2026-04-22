from __future__ import annotations

import uuid
from datetime import datetime

from app.models.visit import EntityType
from app.schemas.common import TimestampedRead


class VisitRead(TimestampedRead):
    camera_id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
