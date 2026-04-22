from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentUpdate
from app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
def list_open_incidents(session: Session = Depends(get_db)) -> list:
    return IncidentRepository(session).list_open()


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, session: Session = Depends(get_db)):
    return IncidentService(session).record(
        camera_id=payload.camera_id,
        incident_type=payload.type,
        severity=payload.severity,
        detected_at=payload.detected_at,
        confidence=payload.confidence,
        notes=payload.notes,
    )


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: uuid.UUID, payload: IncidentUpdate, session: Session = Depends(get_db)
):
    incident = IncidentRepository(session).get(incident_id)
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="incident not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(incident, key, value)
    return incident
