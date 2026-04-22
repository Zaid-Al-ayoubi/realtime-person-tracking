import uuid
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.visit import PersonType
from app.schemas.visit import VisitCreate, VisitClose, VisitRead, VisitSummary
from app.services.visit_service import VisitService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db)) -> VisitService:
    return VisitService(db)


@router.post("/", response_model=VisitRead, status_code=status.HTTP_201_CREATED)
async def open_visit(
    payload: VisitCreate,
    svc: VisitService = Depends(_svc),
):
    """Open a new visit session (called by the video processor)."""
    return await svc.open_visit(payload)


@router.patch("/{visit_id}/close", response_model=VisitRead)
async def close_visit(
    visit_id: uuid.UUID,
    payload: VisitClose,
    svc: VisitService = Depends(_svc),
):
    """Close an open visit and compute duration."""
    return await svc.close_visit(visit_id, payload)


@router.get("/", response_model=list[VisitSummary])
async def list_visits(
    visit_date: date = Query(default_factory=date.today),
    person_type: PersonType | None = None,
    camera_id: uuid.UUID | None = None,
    svc: VisitService = Depends(_svc),
):
    return await svc.list_by_date(
        visit_date, person_type=person_type, camera_id=camera_id
    )


@router.get("/{visit_id}", response_model=VisitRead)
async def get_visit(
    visit_id: uuid.UUID,
    svc: VisitService = Depends(_svc),
):
    return await svc.get_or_404(visit_id)


@router.get("/employee/{employee_id}", response_model=list[VisitSummary])
async def employee_visits(
    employee_id: uuid.UUID,
    start: date = Query(...),
    end: date = Query(...),
    svc: VisitService = Depends(_svc),
):
    return await svc.get_employee_visits(employee_id, start, end)


@router.get("/customer/{customer_id}", response_model=list[VisitSummary])
async def customer_visits(
    customer_id: uuid.UUID,
    svc: VisitService = Depends(_svc),
):
    return await svc.get_customer_visits(customer_id)
