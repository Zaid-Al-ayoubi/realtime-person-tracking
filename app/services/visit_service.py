"""
Visit service — opens, updates, and closes presence sessions.
"""
import uuid
from datetime import datetime, date, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.visit import Visit, PersonType
from app.repositories.visit_repo import VisitRepository
from app.schemas.visit import VisitCreate, VisitClose


class VisitService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = VisitRepository(session)

    async def open_visit(self, payload: VisitCreate) -> Visit:
        visit = Visit(
            person_type=payload.person_type.value,
            employee_id=payload.employee_id,
            customer_id=payload.customer_id,
            camera_id=payload.camera_id,
            entry_time=payload.entry_time,
            visit_date=payload.visit_date,
            track_id=payload.track_id,
            session_id=payload.session_id,
        )
        return await self.repo.create(visit)

    async def close_visit(self, visit_id: uuid.UUID, payload: VisitClose) -> Visit:
        visit = await self.repo.get(visit_id)
        if not visit:
            raise NotFoundError("Visit", str(visit_id))
        visit.close(payload.exit_time)
        return visit

    async def get_or_404(self, visit_id: uuid.UUID) -> Visit:
        visit = await self.repo.get(visit_id)
        if not visit:
            raise NotFoundError("Visit", str(visit_id))
        return visit

    async def list_by_date(
        self,
        visit_date: date,
        *,
        person_type: PersonType | None = None,
        camera_id: uuid.UUID | None = None,
    ) -> list[Visit]:
        return await self.repo.get_by_date(
            visit_date, person_type=person_type, camera_id=camera_id
        )

    async def get_employee_visits(
        self, employee_id: uuid.UUID, start: date, end: date
    ) -> list[Visit]:
        return await self.repo.get_employee_visits_in_range(employee_id, start, end)

    async def get_customer_visits(self, customer_id: uuid.UUID) -> list[Visit]:
        return await self.repo.get_customer_visits(customer_id)

    async def close_all_open_in_session(self, session_id: str, exit_time: datetime) -> int:
        """
        Close all visits that are still open at end of a processing session.
        Used by the batch video processor when a segment ends.
        Returns the number of visits closed.
        """
        open_visits = await self.repo.get_open_visits_by_session(session_id)
        for visit in open_visits:
            visit.close(exit_time)
        return len(open_visits)
