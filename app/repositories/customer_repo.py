from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_all_with_embeddings(self) -> list[Customer]:
        """All customer profiles that have a stored face embedding."""
        result = await self.session.execute(
            select(Customer).where(Customer.face_embedding.is_not(None))
        )
        return list(result.scalars().all())

    async def get_recurring(self) -> list[Customer]:
        result = await self.session.execute(
            select(Customer).where(Customer.is_recurring == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def increment_visit_count(self, customer_id, threshold: int) -> Customer | None:
        """
        Atomically increment visit_count and set is_recurring if threshold reached.
        Returns the updated customer.
        """
        customer = await self.get(customer_id)
        if customer is None:
            return None
        customer.visit_count += 1
        if customer.visit_count >= threshold:
            customer.is_recurring = True
        await self.session.flush()
        await self.session.refresh(customer)
        return customer
