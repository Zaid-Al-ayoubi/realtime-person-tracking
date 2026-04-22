"""
Incident service — records safety events and hands off to the recorder.

Decoupled from analytics: this service doesn't touch visits, detections,
or identity. It just persists an Incident row and (in Phase 2) tells the
IncidentRecorder worker to seal a clip.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.incident import Incident, IncidentSeverity, IncidentStatus, IncidentType
from app.repositories.incident_repository import IncidentRepository

logger = logging.getLogger(__name__)


class IncidentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._repo = IncidentRepository(session)

    def record(
        self,
        *,
        camera_id: uuid.UUID,
        incident_type: IncidentType,
        severity: IncidentSeverity = IncidentSeverity.medium,
        detected_at: datetime | None = None,
        confidence: float | None = None,
        notes: str | None = None,
    ) -> Incident:
        detected_at = detected_at or datetime.now(timezone.utc)
        incident = Incident(
            camera_id=camera_id,
            type=incident_type,
            severity=severity,
            status=IncidentStatus.open,
            detected_at=detected_at,
            confidence=confidence,
            notes=notes,
        )
        self._repo.add(incident)
        logger.warning(
            "incident.recorded",
            extra={
                "incident_id": str(incident.id),
                "type": incident_type.value,
                "severity": severity.value,
            },
        )
        return incident

    def attach_clip(self, incident_id: uuid.UUID, clip_path: str) -> Incident | None:
        incident = self._repo.get(incident_id)
        if incident is None:
            return None
        incident.clip_path = clip_path
        return incident
