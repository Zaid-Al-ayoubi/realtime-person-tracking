from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    DailySummary,
    EmployeeAttendanceRecord,
    DashboardSnapshot,
    HourlyTraffic,
)

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/dashboard", response_model=DashboardSnapshot)
async def dashboard_snapshot(
    svc: AnalyticsService = Depends(_svc),
):
    """
    Lightweight real-time snapshot for the live dashboard header:
    active employees, people in store, open incidents, today's visitor count.
    """
    return await svc.get_dashboard_snapshot()


@router.get("/daily", response_model=DailySummary)
async def daily_summary(
    summary_date: date = Query(default_factory=date.today),
    svc: AnalyticsService = Depends(_svc),
):
    """Full daily analytics summary for the reporting view."""
    return await svc.get_daily_summary(summary_date)


@router.get("/attendance", response_model=list[EmployeeAttendanceRecord])
async def employee_attendance(
    target_date: date = Query(default_factory=date.today),
    svc: AnalyticsService = Depends(_svc),
):
    """Per-employee attendance records for a given date (present/absent/active)."""
    return await svc.get_employee_attendance(target_date)


@router.get("/traffic/hourly", response_model=list[HourlyTraffic])
async def hourly_traffic(
    target_date: date = Query(default_factory=date.today),
    svc: AnalyticsService = Depends(_svc),
):
    """Visitor + employee counts per hour of day — powers the traffic chart."""
    return await svc.get_hourly_traffic(target_date)
