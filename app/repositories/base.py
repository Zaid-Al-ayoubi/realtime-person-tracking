"""
Generic async repository base. Concrete repos extend this and add
domain-specific query methods.
"""
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: UUID) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def list(
        self, *, offset: int = 0, limit: int = 100, **filters: Any
    ) -> list[ModelT]:
        stmt = select(self.model)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update_fields(self, id: UUID, **values: Any) -> ModelT | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id)  # type: ignore[attr-defined]
            .values(**values)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, id: UUID) -> bool:
        stmt = delete(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def count(self, **filters: Any) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one()
