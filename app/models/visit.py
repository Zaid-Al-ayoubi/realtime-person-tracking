from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class EntityType(str, enum.Enum):
    employee = "employee"
    customer = "customer"
    unknown = "unknown"


class Visit(UUIDPKMixin, TimestampMixin, Base):
    """
    A single in-store session for one resolved identity.

    `entity_id` is nullable: visits that never resolved to a stable identity
    (pure unknowns) are still recorded for analytics counts.
    """

    __tablename__ = "visits"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entity_type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type"), nullable=False,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_visits_entity", "entity_type", "entity_id"),
        Index("ix_visits_started_at", "started_at"),
    )
