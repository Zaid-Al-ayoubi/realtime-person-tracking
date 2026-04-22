import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerRead
from app.services.customer_service import CustomerService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db)) -> CustomerService:
    return CustomerService(db)


@router.get("/", response_model=list[CustomerRead])
async def list_customers(
    recurring_only: bool = False,
    svc: CustomerService = Depends(_svc),
):
    customers = await svc.list_all(recurring_only=recurring_only)
    result = []
    for c in customers:
        data = CustomerRead.model_validate(c)
        data.has_face_embedding = c.face_embedding is not None
        result.append(data)
    return result


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: uuid.UUID,
    svc: CustomerService = Depends(_svc),
):
    c = await svc.get_or_404(customer_id)
    data = CustomerRead.model_validate(c)
    data.has_face_embedding = c.face_embedding is not None
    return data


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    svc: CustomerService = Depends(_svc),
):
    c = await svc.update(customer_id, payload)
    data = CustomerRead.model_validate(c)
    data.has_face_embedding = c.face_embedding is not None
    return data


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    svc: CustomerService = Depends(_svc),
):
    await svc.delete(customer_id)
