"""
Visit service — opens, keeps-alive, and closes Visit rows.

Rule: we never open two parallel open visits for the same (entity_type, entity_id).
If a person leaves and returns within `visit_idle_timeout_seconds`, the same
visit is extended. Otherwise a new visit is opened.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.visit import EntityType, Visit
from app.repositories.visit_repository import VisitRepository

logger = logging.getLogger(__name__)


class VisitService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._repo = VisitRepository(session)

    def record_presence(
        self,
        *,
        camera_id: uuid.UUID,
        entity_type: EntityType,
        entity_id: uuid.UUID | None,
        observed_at: datetime | None = None,
    ) -> Visit:
        observed_at = observed_at or datetime.now(timezone.utc)

        open_visit = self._repo.find_open_visit(entity_type=entity_type, entity_id=entity_id)
        if open_visit is not None:
            return open_visit

        visit = Visit(
            camera_id=camera_id,
            entity_type=entity_type,
            entity_id=entity_id,
            started_at=observed_at,
        )
        self._repo.add(visit)
        logger.info(
            "visit.opened",
            extra={
                "visit_id": str(visit.id),
                "entity_type": entity_type.value,
                "entity_id": str(entity_id) if entity_id else None,
            },
        )
        return visit

    def close_idle_visits(self, *, now: datetime | None = None) -> int:
        """
        Close any open visit whose last activity is older than the idle
        timeout. Returns number of visits closed. The pipeline calls this
        periodically.
        """
        now = now or datetime.now(timezone.utc)
        threshold = now - timedelta(seconds=settings.visit_idle_timeout_seconds)

        # For MVP we use Visit.started_at as a proxy for last activity.
        # In Phase 2 we'll attach a last_seen_at column updated from detection logs.
        count = 0
        for visit in self._repo.list_in_range(
            start=datetime(1970, 1, 1, tzinfo=timezone.utc), end=threshold
        ):
            if visit.ended_at is not None:
                continue
            self._close_visit(visit, ended_at=now)
            count += 1
        if count:
            logger.info("visit.idle_closed", extra={"count": count})
        return count

    def _close_visit(self, visit: Visit, *, ended_at: datetime) -> None:
        visit.ended_at = ended_at
        visit.duration_seconds = int((ended_at - visit.started_at).total_seconds())
