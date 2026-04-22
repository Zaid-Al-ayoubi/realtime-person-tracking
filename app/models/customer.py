from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Customer(UUIDPKMixin, TimestampMixin, Base):
    """
    A recurring customer. Rows are created *only* after an unknown candidate
    has been observed enough times (see UnknownCandidate + IdentityService).
    Names are optional — most rows are anonymous but stable.
    """

    __tablename__ = "customers"

    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
