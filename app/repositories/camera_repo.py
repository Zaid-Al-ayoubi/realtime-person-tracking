from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import Camera
from app.repositories.base import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    model = Camera

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_active(self) -> list[Camera]:
        result = await self.session.execute(
            select(Camera).where(Camera.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())
