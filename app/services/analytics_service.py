"""
Analytics service — aggregates data for dashboard endpoints.
Reads from multiple repos to compose summary views.
"""
from datetime import date, datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visit import Visit, PersonType
from app.models.employee import Employee
from app.models.customer import Customer
from app.models.incident import Incident, IncidentStatus
from app.repositories.visit_repo import VisitRepository
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.incident_repo import IncidentRepository
from app.schemas.analytics import (
    DailySummary,
    EmployeeAttendanceRecord,
    DashboardSnapshot,
    HourlyTraffic,
)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.visit_repo = VisitRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.incident_repo = IncidentRepository(session)

    async def get_daily_summary(self, summary_date: date) -> DailySummary:
        # Visitor counts by type
        total_visitors = await self.visit_repo.count_by_date_and_type(
            summary_date, PersonType.EMPLOYEE
        ) + await self.visit_repo.count_by_date_and_type(
            summary_date, PersonType.CUSTOMER
        ) + await self.visit_repo.count_by_date_and_type(
            summary_date, PersonType.UNKNOWN
        )

        # Unique customers (distinct customer_id)
        result = await self.session.execute(
            select(func.count(func.distinct(Visit.customer_id))).where(
                and_(Visit.visit_date == summary_date, Visit.customer_id.is_not(None))
            )
        )
        unique_customers = result.scalar_one() or 0

        # Recurring customers
        result = await self.session.execute(
            select(func.count(func.distinct(Visit.customer_id)))
            .join(Customer, Visit.customer_id == Customer.id)
            .where(
                and_(
                    Visit.visit_date == summary_date,
                    Customer.is_recurring == True,  # noqa: E712
                )
            )
        )
        recurring_customers = result.scalar_one() or 0

        unknown_count = await self.visit_repo.count_by_date_and_type(
            summary_date, PersonType.UNKNOWN
        )

        # Employee attendance
        all_employees = await self.employee_repo.list_active()
        present_ids_result = await self.session.execute(
            select(func.distinct(Visit.employee_id)).where(
                and_(
                    Visit.visit_date == summary_date,
                    Visit.employee_id.is_not(None),
                )
            )
        )
        present_ids = {row[0] for row in present_ids_result.fetchall()}
        employees_present = len(present_ids)
        employees_absent = len(all_employees) - employees_present

        # Incidents
        day_incidents = await self.incident_repo.get_by_date(summary_date)
        total_incidents = len(day_incidents)

        # Avg customer stay
        avg_secs = await self.visit_repo.avg_duration_by_date(summary_date, PersonType.CUSTOMER)
        avg_stay_min = round(avg_secs / 60, 1) if avg_secs else None

        # Peak hour
        result = await self.session.execute(
            select(
                func.extract("hour", Visit.entry_time).label("hour"),
                func.count().label("cnt"),
            )
            .where(Visit.visit_date == summary_date)
            .group_by("hour")
            .order_by(func.count().desc())
            .limit(1)
        )
        row = result.first()
        peak_hour = int(row[0]) if row else None

        return DailySummary(
            summary_date=summary_date,
            total_visitors=total_visitors,
            unique_customers=unique_customers,
            recurring_customers=recurring_customers,
            unknown_visitors=unknown_count,
            employees_present=employees_present,
            employees_absent=max(0, employees_absent),
            total_incidents=total_incidents,
            avg_customer_stay_minutes=avg_stay_min,
            peak_hour=peak_hour,
        )

    async def get_employee_attendance(
        self, target_date: date
    ) -> list[EmployeeAttendanceRecord]:
        employees = await self.employee_repo.list_active()
        records: list[EmployeeAttendanceRecord] = []

        for emp in employees:
            visits = await self.visit_repo.get_employee_visits_in_range(
                emp.id, target_date, target_date
            )
            if not visits:
                records.append(
                    EmployeeAttendanceRecord(
                        employee_id=str(emp.id),
                        name=emp.name,
                        role=emp.role,
                        entry_time=None,
                        exit_time=None,
                        hours_worked=None,
                        status="absent",
                    )
                )
                continue

            first_entry = min(v.entry_time for v in visits)
            last_exit = max(
                (v.exit_time for v in visits if v.exit_time), default=None
            )
            total_secs = sum(v.duration_seconds or 0 for v in visits)
            hours = round(total_secs / 3600, 2) if total_secs else None
            status = "active" if any(v.exit_time is None for v in visits) else "present"

            records.append(
                EmployeeAttendanceRecord(
                    employee_id=str(emp.id),
                    name=emp.name,
                    role=emp.role,
                    entry_time=first_entry,
                    exit_time=last_exit,
                    hours_worked=hours,
                    status=status,
                )
            )

        return records

    async def get_dashboard_snapshot(self) -> DashboardSnapshot:
        today = date.today()
        now = datetime.now(timezone.utc)

        # Active employees — visits open today with no exit_time
        result = await self.session.execute(
            select(Visit, Employee)
            .join(Employee, Visit.employee_id == Employee.id)
            .where(
                and_(
                    Visit.visit_date == today,
                    Visit.exit_time.is_(None),
                    Visit.employee_id.is_not(None),
                )
            )
        )
        active_records = []
        for visit, emp in result.all():
            active_records.append(
                EmployeeAttendanceRecord(
                    employee_id=str(emp.id),
                    name=emp.name,
                    role=emp.role,
                    entry_time=visit.entry_time,
                    exit_time=None,
                    hours_worked=None,
                    status="active",
                )
            )

        # People in store (all open visits today, any type)
        result = await self.session.execute(
            select(func.count()).select_from(Visit).where(
                and_(Visit.visit_date == today, Visit.exit_time.is_(None))
            )
        )
        people_in_store = result.scalar_one() or 0

        # Open incidents
        open_incidents = await self.incident_repo.get_open()

        # Today's visitors / recurring
        today_visitors = await self.visit_repo.count_by_date_and_type(
            today, PersonType.CUSTOMER
        ) + await self.visit_repo.count_by_date_and_type(today, PersonType.UNKNOWN)

        result = await self.session.execute(
            select(func.count(func.distinct(Visit.customer_id)))
            .join(Customer, Visit.customer_id == Customer.id)
            .where(
                and_(
                    Visit.visit_date == today,
                    Customer.is_recurring == True,  # noqa: E712
                )
            )
        )
        today_recurring = result.scalar_one() or 0

        return DashboardSnapshot(
            as_of=now,
            active_employees=active_records,
            people_in_store=people_in_store,
            open_incidents=len(open_incidents),
            today_visitors=today_visitors,
            today_recurring=today_recurring,
        )

    async def get_hourly_traffic(self, target_date: date) -> list[HourlyTraffic]:
        result = await self.session.execute(
            select(
                func.extract("hour", Visit.entry_time).label("hour"),
                func.count().label("total"),
                func.sum(
                    func.cast(Visit.person_type == PersonType.EMPLOYEE.value, func.Integer if False else type(1))
                ).label("emp_count"),
            )
            .where(Visit.visit_date == target_date)
            .group_by("hour")
            .order_by("hour")
        )

        traffic = []
        for row in result.all():
            hour = int(row[0])
            total = int(row[1])
            # Simpler approach — fetch employee count separately
            emp_result = await self.session.execute(
                select(func.count()).select_from(Visit).where(
                    and_(
                        Visit.visit_date == target_date,
                        func.extract("hour", Visit.entry_time) == hour,
                        Visit.person_type == PersonType.EMPLOYEE.value,
                    )
                )
            )
            emp_count = emp_result.scalar_one() or 0
            traffic.append(
                HourlyTraffic(hour=hour, visitor_count=total - emp_count, employee_count=emp_count)
            )

        return traffic
