from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, select

from app.models.visit import EntityType, Visit
from app.repositories.base import BaseRepository


class VisitRepository(BaseRepository[Visit]):
    model = Visit

    def find_open_visit(
        self, *, entity_type: EntityType, entity_id: uuid.UUID | None
    ) -> Visit | None:
        """Return the most recent visit for this entity that has no end time."""
        stmt = (
            select(Visit)
            .where(
                and_(
                    Visit.entity_type == entity_type,
                    Visit.entity_id == entity_id,
                    Visit.ended_at.is_(None),
                )
            )
            .order_by(Visit.started_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_in_range(self, start: datetime, end: datetime) -> list[Visit]:
        stmt = (
            select(Visit)
            .where(and_(Visit.started_at >= start, Visit.started_at < end))
            .order_by(Visit.started_at.asc())
        )
        return list(self.session.scalars(stmt).all())
