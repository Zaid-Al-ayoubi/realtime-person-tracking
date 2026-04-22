import uuid
import enum
from datetime import datetime, date
from sqlalchemy import String, Integer, ForeignKey, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models.mixins import TimestampMixin


class PersonType(str, enum.Enum):
    EMPLOYEE = "employee"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


class Visit(Base, TimestampMixin):
    """
    One visit session for a person (employee or customer).

    entry_time / exit_time define the presence window. duration_seconds is
    computed on session close. Visits for unknown persons have no employee_id
    or customer_id — they are linked later if the unknown is resolved.

    track_id  — the ByteTrack ID valid only within one processing session.
    session_id — the processing batch/session reference (e.g. video chunk UUID).
    """

    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    person_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Exactly one of these should be set for identified persons
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), index=True
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="SET NULL"), index=True
    )

    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Temporary tracking reference — not a persistent identity
    track_id: Mapped[str | None] = mapped_column(String(100))
    session_id: Mapped[str | None] = mapped_column(String(100), index=True)

    # Relationships
    employee: Mapped["Employee | None"] = relationship(  # noqa: F821
        "Employee", back_populates="visits", foreign_keys=[employee_id]
    )
    customer: Mapped["Customer | None"] = relationship(  # noqa: F821
        "Customer", back_populates="visits", foreign_keys=[customer_id]
    )
    camera: Mapped["Camera | None"] = relationship("Camera", back_populates="visits")  # noqa: F821
    detection_logs: Mapped[list["DetectionLog"]] = relationship(  # noqa: F821
        "DetectionLog", back_populates="visit"
    )

    def close(self, exit_time: datetime) -> None:
        """Finalise the visit by computing duration."""
        self.exit_time = exit_time
        delta = exit_time - self.entry_time
        self.duration_seconds = max(0, int(delta.total_seconds()))

    def __repr__(self) -> str:
        return f"<Visit id={self.id} type={self.person_type} date={self.visit_date}>"
