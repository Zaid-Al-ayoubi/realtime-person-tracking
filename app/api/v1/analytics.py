from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ------------------------------------------------------------------ #
# Response schemas
# ------------------------------------------------------------------ #

class DailySummaryResponse(BaseModel):
    day: date_type
    employee_visits: int
    customer_visits: int
    unknown_visits: int
    recurring_customers: int
    incidents: int
    avg_customer_stay_minutes: Optional[float]
    peak_hour: Optional[int]


class EmployeeAttendanceResponse(BaseModel):
    employee_id: uuid.UUID
    full_name: str
    role: Optional[str]
    status: str  # "present" | "absent" | "currently_in"
    first_entry: Optional[datetime]
    last_exit: Optional[datetime]
    total_minutes: float


class HourlyBucketResponse(BaseModel):
    hour: int
    employee_count: int
    customer_count: int
    unknown_count: int


class DashboardSnapshotResponse(BaseModel):
    as_of: datetime
    people_in_store: int
    employees_in_store: int
    open_incidents: int
    today_customer_visits: int
    today_recurring: int


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #

@router.get("/dashboard", response_model=DashboardSnapshotResponse)
def dashboard_snapshot(session: Session = Depends(get_db)) -> DashboardSnapshotResponse:
    """Live snapshot: who is in-store right now, open incidents, today's traffic."""
    snap = AnalyticsService(session).dashboard_snapshot()
    return DashboardSnapshotResponse(**snap.__dict__)


@router.get("/daily", response_model=DailySummaryResponse)
def daily_summary(
    day: date_type = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    session: Session = Depends(get_db),
) -> DailySummaryResponse:
    """Aggregate visit and incident counts for a given day."""
    summary = AnalyticsService(session).daily_summary(day)
    return DailySummaryResponse(**summary.__dict__)


@router.get("/attendance", response_model=list[EmployeeAttendanceResponse])
def employee_attendance(
    day: date_type = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    session: Session = Depends(get_db),
) -> list[EmployeeAttendanceResponse]:
    """Per-employee attendance for a given day (absent / present / currently_in)."""
    records = AnalyticsService(session).employee_attendance(day)
    return [EmployeeAttendanceResponse(**r.__dict__) for r in records]


@router.get("/traffic/hourly", response_model=list[HourlyBucketResponse])
def hourly_traffic(
    day: date_type = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    session: Session = Depends(get_db),
) -> list[HourlyBucketResponse]:
    """Visitor traffic broken down by hour of day, split by entity type."""
    buckets = AnalyticsService(session).hourly_traffic(day)
    return [HourlyBucketResponse(**b.__dict__) for b in buckets]
