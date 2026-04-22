"""
Customer service — manages customer profiles and recurring-customer promotion logic.
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError
from app.models.customer import Customer
from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = CustomerRepository(session)

    async def create(self, payload: CustomerCreate) -> Customer:
        customer = Customer(**payload.model_dump())
        return await self.repo.create(customer)

    async def get_or_404(self, customer_id: uuid.UUID) -> Customer:
        customer = await self.repo.get(customer_id)
        if not customer:
            raise NotFoundError("Customer", str(customer_id))
        return customer

    async def list_all(self, *, recurring_only: bool = False) -> list[Customer]:
        if recurring_only:
            return await self.repo.get_recurring()
        return await self.repo.list()

    async def update(self, customer_id: uuid.UUID, payload: CustomerUpdate) -> Customer:
        customer = await self.get_or_404(customer_id)
        data = payload.model_dump(exclude_unset=True)
        for key, val in data.items():
            setattr(customer, key, val)
        return customer

    async def update_embedding(
        self, customer_id: uuid.UUID, embedding: list[float], image_path: str | None = None
    ) -> Customer:
        customer = await self.get_or_404(customer_id)
        customer.face_embedding = embedding
        if image_path:
            customer.face_image_path = image_path
        return customer

    async def record_new_visit(self, customer_id: uuid.UUID) -> Customer:
        """
        Called when a known customer is detected. Increments visit_count
        and promotes to recurring status if threshold is met.
        """
        customer = await self.repo.increment_visit_count(
            customer_id, threshold=settings.RECURRING_CUSTOMER_MIN_VISITS
        )
        if not customer:
            raise NotFoundError("Customer", str(customer_id))
        return customer

    async def get_all_with_embeddings(self) -> list[Customer]:
        return await self.repo.get_all_with_embeddings()

    async def create_unknown_with_embedding(
        self, embedding: list[float], image_path: str | None = None
    ) -> Customer:
        """
        Bootstrap a new unknown customer profile from their first detected face.
        They start with visit_count=1 and is_recurring=False.
        The identity_service decides when to call this.
        """
        customer = Customer(
            face_embedding=embedding,
            face_image_path=image_path,
            visit_count=1,
            is_recurring=False,
        )
        return await self.repo.create(customer)

    async def delete(self, customer_id: uuid.UUID) -> None:
        deleted = await self.repo.delete(customer_id)
        if not deleted:
            raise NotFoundError("Customer", str(customer_id))
