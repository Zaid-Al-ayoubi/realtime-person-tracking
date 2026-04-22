from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.visit_repository import VisitRepository
from app.schemas.visit import VisitRead

router = APIRouter(prefix="/visits", tags=["visits"])


@router.get("", response_model=list[VisitRead])
def list_visits(
    start: datetime = Query(...),
    end: datetime = Query(...),
    session: Session = Depends(get_db),
) -> list:
    return VisitRepository(session).list_in_range(start, end)
