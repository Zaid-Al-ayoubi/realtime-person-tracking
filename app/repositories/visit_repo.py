from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visit import Visit, PersonType
from app.repositories.base import BaseRepository


class VisitRepository(BaseRepository[Visit]):
    model = Visit

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_open_visits_by_session(self, session_id: str) -> list[Visit]:
        """Return visits that have not been closed yet for a given processing session."""
        result = await self.session.execute(
            select(Visit).where(
                Visit.session_id == session_id,
                Visit.exit_time.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_by_date(
        self,
        visit_date: date,
        *,
        person_type: PersonType | None = None,
        camera_id: UUID | None = None,
    ) -> list[Visit]:
        stmt = select(Visit).where(Visit.visit_date == visit_date)
        if person_type is not None:
            stmt = stmt.where(Visit.person_type == person_type.value)
        if camera_id is not None:
            stmt = stmt.where(Visit.camera_id == camera_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_employee_visits_in_range(
        self, employee_id: UUID, start: date, end: date
    ) -> list[Visit]:
        result = await self.session.execute(
            select(Visit).where(
                Visit.employee_id == employee_id,
                Visit.visit_date >= start,
                Visit.visit_date <= end,
            )
        )
        return list(result.scalars().all())

    async def get_customer_visits(self, customer_id: UUID) -> list[Visit]:
        result = await self.session.execute(
            select(Visit)
            .where(Visit.customer_id == customer_id)
            .order_by(Visit.entry_time.desc())
        )
        return list(result.scalars().all())

    async def count_by_date_and_type(
        self, visit_date: date, person_type: PersonType
    ) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Visit).where(
                and_(
                    Visit.visit_date == visit_date,
                    Visit.person_type == person_type.value,
                )
            )
        )
        return result.scalar_one()

    async def avg_duration_by_date(
        self, visit_date: date, person_type: PersonType
    ) -> float | None:
        result = await self.session.execute(
            select(func.avg(Visit.duration_seconds)).where(
                and_(
                    Visit.visit_date == visit_date,
                    Visit.person_type == person_type.value,
                    Visit.duration_seconds.is_not(None),
                )
            )
        )
        val = result.scalar_one_or_none()
        return float(val) if val is not None else None
