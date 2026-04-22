from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus
from app.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_date(self, target_date: date) -> list[Incident]:
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())
        result = await self.session.execute(
            select(Incident).where(
                and_(
                    Incident.occurred_at >= day_start,
                    Incident.occurred_at <= day_end,
                )
            ).order_by(Incident.occurred_at.desc())
        )
        return list(result.scalars().all())

    async def get_open(self) -> list[Incident]:
        result = await self.session.execute(
            select(Incident)
            .where(Incident.status == IncidentStatus.PENDING.value)
            .order_by(Incident.occurred_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_camera(self, camera_id: UUID) -> list[Incident]:
        result = await self.session.execute(
            select(Incident)
            .where(Incident.camera_id == camera_id)
            .order_by(Incident.occurred_at.desc())
        )
        return list(result.scalars().all())
