from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class DetectionLog(UUIDPKMixin, TimestampMixin, Base):
    """
    Raw detection record. High-volume — we log one row per detected person
    per sampled frame (sampling rate configured in pipeline).

    `track_id` is the *in-session* tracker ID. It is NOT a persistent
    identity — see Visit / FaceEmbedding for that.
    """

    __tablename__ = "detection_logs"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_w: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_h: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    resolved_entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
