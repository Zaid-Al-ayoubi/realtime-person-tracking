import uuid
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.incident import IncidentCreate, IncidentUpdate, IncidentRead
from app.services.incident_service import IncidentService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db)) -> IncidentService:
    return IncidentService(db)


@router.post("/", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    svc: IncidentService = Depends(_svc),
):
    """Report a new incident (can be triggered by automated detector or manual report)."""
    return await svc.create(payload)


@router.get("/", response_model=list[IncidentRead])
async def list_incidents(
    incident_date: date = Query(default_factory=date.today),
    svc: IncidentService = Depends(_svc),
):
    return await svc.list_by_date(incident_date)


@router.get("/open", response_model=list[IncidentRead])
async def list_open_incidents(
    svc: IncidentService = Depends(_svc),
):
    """All pending/unreviewed incidents — used by live dashboard alert panel."""
    return await svc.list_open()


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: uuid.UUID,
    svc: IncidentService = Depends(_svc),
):
    return await svc.get_or_404(incident_id)


@router.patch("/{incident_id}", response_model=IncidentRead)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    svc: IncidentService = Depends(_svc),
):
    """Update status, severity, notes, or attach video paths."""
    return await svc.update(incident_id, payload)
