from __future__ import annotations

from sqlalchemy import select

from app.models.camera import Camera
from app.repositories.base import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    model = Camera

    def get_by_name(self, name: str) -> Camera | None:
        stmt = select(Camera).where(Camera.name == name)
        return self.session.scalars(stmt).first()

    def list_active(self) -> list[Camera]:
        stmt = select(Camera).where(Camera.is_active.is_(True))
        return list(self.session.scalars(stmt).all())
