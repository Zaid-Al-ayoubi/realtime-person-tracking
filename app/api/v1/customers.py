from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    recurring_only: bool = Query(default=False, description="Return only recurring customers"),
    session: Session = Depends(get_db),
) -> list[Customer]:
    repo = CustomerRepository(session)
    if recurring_only:
        return repo.list_recurring()
    return repo.list()


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, session: Session = Depends(get_db)) -> Customer:
    """Manually create a named customer profile (e.g. for loyalty programme enrolment)."""
    return CustomerRepository(session).add(Customer(**payload.model_dump()))


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: uuid.UUID, session: Session = Depends(get_db)) -> Customer:
    customer = CustomerRepository(session).get(customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: uuid.UUID, payload: CustomerUpdate, session: Session = Depends(get_db)
) -> Customer:
    customer = CustomerRepository(session).get(customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="customer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    return customer
