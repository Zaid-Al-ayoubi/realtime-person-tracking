from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, select

from app.models.incident import Incident, IncidentStatus
from app.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    def list_open(self) -> list[Incident]:
        stmt = (
            select(Incident)
            .where(Incident.status == IncidentStatus.open)
            .order_by(Incident.detected_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_in_range(self, start: datetime, end: datetime) -> list[Incident]:
        stmt = (
            select(Incident)
            .where(and_(Incident.detected_at >= start, Incident.detected_at < end))
            .order_by(Incident.detected_at.desc())
        )
        return list(self.session.scalars(stmt).all())
