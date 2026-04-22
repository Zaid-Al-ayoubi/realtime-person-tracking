from __future__ import annotations

from sqlalchemy import select

from app.models.employee import Employee, EmployeeStatus
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    model = Employee

    def get_by_external_ref(self, external_ref: str) -> Employee | None:
        stmt = select(Employee).where(Employee.external_ref == external_ref)
        return self.session.scalars(stmt).first()

    def list_active(self) -> list[Employee]:
        stmt = select(Employee).where(Employee.status == EmployeeStatus.active)
        return list(self.session.scalars(stmt).all())
