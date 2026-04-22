from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class UnknownCandidate(UUIDPKMixin, TimestampMixin, Base):
    """
    Staging identity for a face embedding that has been seen at least once
    but not yet promoted to a Customer. Promotion happens when
    `observation_count >= settings.unknown_promotion_visits`.
    """

    __tablename__ = "unknown_candidates"

    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
