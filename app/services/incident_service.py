"""
Incident service — creates, updates, and queries alert/event records.
Fully decoupled from visit analytics.
"""
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.incident import Incident
from app.repositories.incident_repo import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentUpdate


class IncidentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = IncidentRepository(session)

    async def create(self, payload: IncidentCreate) -> Incident:
        incident = Incident(
            camera_id=payload.camera_id,
            incident_type=payload.incident_type.value,
            severity=payload.severity.value,
            occurred_at=payload.occurred_at,
            confidence=payload.confidence,
            notes=payload.notes,
        )
        return await self.repo.create(incident)

    async def get_or_404(self, incident_id: uuid.UUID) -> Incident:
        incident = await self.repo.get(incident_id)
        if not incident:
            raise NotFoundError("Incident", str(incident_id))
        return incident

    async def update(self, incident_id: uuid.UUID, payload: IncidentUpdate) -> Incident:
        incident = await self.get_or_404(incident_id)
        data = payload.model_dump(exclude_unset=True)
        for key, val in data.items():
            if val is not None:
                # Convert enums to their values
                setattr(incident, key, val.value if hasattr(val, "value") else val)
        return incident

    async def list_by_date(self, target_date: date) -> list[Incident]:
        return await self.repo.get_by_date(target_date)

    async def list_open(self) -> list[Incident]:
        return await self.repo.get_open()

    async def attach_video(
        self,
        incident_id: uuid.UUID,
        *,
        clip_path: str | None = None,
        pre_event_path: str | None = None,
    ) -> Incident:
        incident = await self.get_or_404(incident_id)
        if clip_path:
            incident.video_clip_path = clip_path
        if pre_event_path:
            incident.video_pre_event_path = pre_event_path
        return incident
