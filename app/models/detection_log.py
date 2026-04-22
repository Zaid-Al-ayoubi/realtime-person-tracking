import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class DetectionLog(Base):
    """
    Low-level detection record per frame/event. High volume — consider
    partitioning by date in production. Linked to a Visit once identity is resolved.
    bbox format: {"x1": int, "y1": int, "x2": int, "y2": int}
    """

    __tablename__ = "detection_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visits.id", ondelete="SET NULL"), index=True
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="SET NULL"), index=True
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    track_id: Mapped[str | None] = mapped_column(String(100), index=True)
    person_type: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    face_detected: Mapped[bool | None] = mapped_column(Boolean)
    face_confidence: Mapped[float | None] = mapped_column(Float)

    # Bounding box as JSONB: {"x1":..,"y1":..,"x2":..,"y2":..}
    bbox: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    visit: Mapped["Visit | None"] = relationship("Visit", back_populates="detection_logs")  # noqa: F821

    def __repr__(self) -> str:
        return f"<DetectionLog id={self.id} ts={self.timestamp} track={self.track_id}>"
