from __future__ import annotations

from sqlalchemy import select

from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    def list_recurring(self) -> list[Customer]:
        """Return customers with visit_count >= 2 (promoted from unknown)."""
        stmt = select(Customer).where(Customer.visit_count >= 2).order_by(Customer.visit_count.desc())
        return list(self.session.scalars(stmt).all())
