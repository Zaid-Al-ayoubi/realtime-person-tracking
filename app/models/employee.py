from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class EmployeeStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    terminated = "terminated"


class Employee(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True,
        doc="HR system ID / employee code, if any.",
    )
    status: Mapped[EmployeeStatus] = mapped_column(
        SAEnum(EmployeeStatus, name="employee_status"),
        nullable=False,
        default=EmployeeStatus.active,
    )
    is_enrolled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        doc="True once at least one face embedding has been registered.",
    )
