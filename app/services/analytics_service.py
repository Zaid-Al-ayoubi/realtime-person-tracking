"""
Analytics service — read-side aggregations for the dashboard.

For Phase 1 we expose the shape of the API; implementations are concrete
but intentionally simple. Real-world rollups (daily/weekly/monthly)
become materialized views or dedicated summary tables in Phase 2.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.employee import Employee, EmployeeStatus
from app.models.incident import Incident, IncidentStatus
from app.models.visit import EntityType, Visit


@dataclass(frozen=True)
class DailySummary:
    day: date
    employee_visits: int
    customer_visits: int
    unknown_visits: int
    recurring_customers: int
    incidents: int
    avg_customer_stay_minutes: Optional[float]
    peak_hour: Optional[int]


@dataclass(frozen=True)
class EmployeeAttendanceRecord:
    employee_id: uuid.UUID
    full_name: str
    role: Optional[str]
    status: str  # "present" | "absent" | "currently_in"
    first_entry: Optional[datetime]
    last_exit: Optional[datetime]
    total_minutes: float


@dataclass(frozen=True)
class HourlyBucket:
    hour: int
    employee_count: int
    customer_count: int
    unknown_count: int


@dataclass(frozen=True)
class DashboardSnapshot:
    as_of: datetime
    people_in_store: int
    employees_in_store: int
    open_incidents: int
    today_customer_visits: int
    today_recurring: int


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ #
    # Core daily summary
    # ------------------------------------------------------------------ #

    def daily_summary(self, day: date) -> DailySummary:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)

        counts = dict(
            self.session.execute(
                select(Visit.entity_type, func.count())
                .where(Visit.started_at >= start, Visit.started_at <= end)
                .group_by(Visit.entity_type)
            ).all()
        )

        incident_count = self.session.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.detected_at >= start, Incident.detected_at <= end)
        ) or 0

        # Recurring = customers whose visit_count >= 2 and visited today
        recurring_count = self.session.scalar(
            select(func.count(func.distinct(Visit.entity_id)))
            .join(Customer, Visit.entity_id == Customer.id)
            .where(
                and_(
                    Visit.started_at >= start,
                    Visit.started_at <= end,
                    Visit.entity_type == EntityType.customer,
                    Customer.visit_count >= 2,
                )
            )
        ) or 0

        # Average customer stay duration (seconds → minutes)
        avg_secs = self.session.scalar(
            select(func.avg(Visit.duration_seconds))
            .where(
                and_(
                    Visit.started_at >= start,
                    Visit.started_at <= end,
                    Visit.entity_type == EntityType.customer,
                    Visit.duration_seconds.is_not(None),
                )
            )
        )
        avg_minutes = round(float(avg_secs) / 60, 1) if avg_secs else None

        # Peak hour
        peak_row = self.session.execute(
            select(
                func.extract("hour", Visit.started_at).label("hr"),
                func.count().label("cnt"),
            )
            .where(Visit.started_at >= start, Visit.started_at <= end)
            .group_by("hr")
            .order_by(func.count().desc())
            .limit(1)
        ).first()
        peak_hour = int(peak_row[0]) if peak_row else None

        return DailySummary(
            day=day,
            employee_visits=counts.get(EntityType.employee, 0),
            customer_visits=counts.get(EntityType.customer, 0),
            unknown_visits=counts.get(EntityType.unknown, 0),
            recurring_customers=int(recurring_count),
            incidents=int(incident_count),
            avg_customer_stay_minutes=avg_minutes,
            peak_hour=peak_hour,
        )

    # ------------------------------------------------------------------ #
    # Employee attendance for a given day
    # ------------------------------------------------------------------ #

    def employee_attendance(self, day: date) -> list[EmployeeAttendanceRecord]:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)

        employees = self.session.scalars(
            select(Employee).where(Employee.status == EmployeeStatus.active)
        ).all()

        records: list[EmployeeAttendanceRecord] = []
        for emp in employees:
            visits = list(
                self.session.scalars(
                    select(Visit).where(
                        and_(
                            Visit.entity_type == EntityType.employee,
                            Visit.entity_id == emp.id,
                            Visit.started_at >= start,
                            Visit.started_at <= end,
                        )
                    )
                ).all()
            )

            if not visits:
                records.append(EmployeeAttendanceRecord(
                    employee_id=emp.id,
                    full_name=emp.full_name,
                    role=emp.role,
                    status="absent",
                    first_entry=None,
                    last_exit=None,
                    total_minutes=0.0,
                ))
                continue

            first_entry = min(v.started_at for v in visits)
            last_exit = max((v.ended_at for v in visits if v.ended_at), default=None)
            total_secs = sum(v.duration_seconds or 0 for v in visits)
            currently_in = any(v.ended_at is None for v in visits)

            records.append(EmployeeAttendanceRecord(
                employee_id=emp.id,
                full_name=emp.full_name,
                role=emp.role,
                status="currently_in" if currently_in else "present",
                first_entry=first_entry,
                last_exit=last_exit,
                total_minutes=round(total_secs / 60, 1),
            ))

        return records

    # ------------------------------------------------------------------ #
    # Hourly traffic breakdown
    # ------------------------------------------------------------------ #

    def hourly_traffic(self, day: date) -> list[HourlyBucket]:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)

        rows = self.session.execute(
            select(
                func.extract("hour", Visit.started_at).label("hr"),
                Visit.entity_type,
                func.count().label("cnt"),
            )
            .where(Visit.started_at >= start, Visit.started_at <= end)
            .group_by("hr", Visit.entity_type)
            .order_by("hr")
        ).all()

        buckets: dict[int, dict] = {}
        for hr, etype, cnt in rows:
            h = int(hr)
            if h not in buckets:
                buckets[h] = {"employee": 0, "customer": 0, "unknown": 0}
            buckets[h][etype.value] = int(cnt)

        return [
            HourlyBucket(
                hour=h,
                employee_count=b["employee"],
                customer_count=b["customer"],
                unknown_count=b["unknown"],
            )
            for h, b in sorted(buckets.items())
        ]

    # ------------------------------------------------------------------ #
    # Live dashboard snapshot
    # ------------------------------------------------------------------ #

    def dashboard_snapshot(self) -> DashboardSnapshot:
        now = datetime.now(timezone.utc)
        today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

        # People with open visits (no ended_at)
        people_in = self.session.scalar(
            select(func.count()).select_from(Visit).where(Visit.ended_at.is_(None))
        ) or 0
        employees_in = self.session.scalar(
            select(func.count()).select_from(Visit).where(
                and_(Visit.ended_at.is_(None), Visit.entity_type == EntityType.employee)
            )
        ) or 0

        open_incidents = self.session.scalar(
            select(func.count()).select_from(Incident)
            .where(Incident.status == IncidentStatus.open)
        ) or 0

        today_customers = self.session.scalar(
            select(func.count()).select_from(Visit)
            .where(
                and_(
                    Visit.started_at >= today_start,
                    Visit.entity_type == EntityType.customer,
                )
            )
        ) or 0

        today_recurring = self.session.scalar(
            select(func.count(func.distinct(Visit.entity_id)))
            .join(Customer, Visit.entity_id == Customer.id)
            .where(
                and_(
                    Visit.started_at >= today_start,
                    Visit.entity_type == EntityType.customer,
                    Customer.visit_count >= 2,
                )
            )
        ) or 0

        return DashboardSnapshot(
            as_of=now,
            people_in_store=int(people_in),
            employees_in_store=int(employees_in),
            open_incidents=int(open_incidents),
            today_customer_visits=int(today_customers),
            today_recurring=int(today_recurring),
        )
