from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    model = Employee

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_code(self, employee_code: str) -> Employee | None:
        result = await self.session.execute(
            select(Employee).where(Employee.employee_code == employee_code)
        )
        return result.scalar_one_or_none()

    async def get_all_with_embeddings(self) -> list[Employee]:
        """Return active employees that have a face embedding registered."""
        result = await self.session.execute(
            select(Employee).where(
                Employee.is_active == True,  # noqa: E712
                Employee.face_embedding.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def list_active(self) -> list[Employee]:
        result = await self.session.execute(
            select(Employee).where(Employee.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())
