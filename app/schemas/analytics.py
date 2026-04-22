from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class DailySummary(BaseModel):
    """Top-level daily analytics snapshot for the dashboard."""
    summary_date: date
    total_visitors: int
    unique_customers: int
    recurring_customers: int
    unknown_visitors: int
    employees_present: int
    employees_absent: int
    total_incidents: int
    avg_customer_stay_minutes: Optional[float] = None
    peak_hour: Optional[int] = None  # 0-23


class EmployeeAttendanceRecord(BaseModel):
    employee_id: str
    name: str
    role: Optional[str]
    entry_time: Optional[datetime]
    exit_time: Optional[datetime]
    hours_worked: Optional[float]
    status: str  # "present" | "absent" | "active"


class CustomerVisitRecord(BaseModel):
    customer_id: str
    name: Optional[str]
    visit_count: int
    is_recurring: bool
    last_visit: Optional[datetime]
    avg_stay_minutes: Optional[float]


class HourlyTraffic(BaseModel):
    hour: int  # 0-23
    visitor_count: int
    employee_count: int


class WeeklySummary(BaseModel):
    week_start: date
    week_end: date
    total_visitors: int
    recurring_customers: int
    total_incidents: int
    daily_traffic: list[HourlyTraffic] = []


class DashboardSnapshot(BaseModel):
    """Real-time lightweight snapshot for the live dashboard."""
    as_of: datetime
    active_employees: list[EmployeeAttendanceRecord]
    people_in_store: int
    open_incidents: int
    today_visitors: int
    today_recurring: int
