import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models.mixins import TimestampMixin


class IncidentType(str, enum.Enum):
    FIRE = "fire"
    FIGHT = "fight"
    VIOLENCE = "violence"
    EMERGENCY = "emergency"
    SUSPICIOUS = "suspicious"
    OTHER = "other"


class IncidentSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"


class Incident(Base, TimestampMixin):
    """
    An alert/event detected by the system (fire, fight, etc.).

    video_clip_path     — the post-event clip saved to disk
    video_pre_event_path — pre-event buffer clip (up to 15 min before)

    Decoupled from visit analytics intentionally.
    """

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="SET NULL"), index=True
    )

    incident_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        String(20), default=IncidentSeverity.MEDIUM.value, nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    video_clip_path: Mapped[str | None] = mapped_column(String(500))
    video_pre_event_path: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(
        String(30), default=IncidentStatus.PENDING.value, nullable=False, index=True
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    camera: Mapped["Camera | None"] = relationship("Camera", back_populates="incidents")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Incident id={self.id} type={self.incident_type} severity={self.severity}>"
