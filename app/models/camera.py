from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Camera(UUIDPKMixin, TimestampMixin, Base):
    """A physical or logical camera source (webcam, RTSP URL, or video file)."""

    __tablename__ = "cameras"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(
        Text, nullable=False,
        doc="Opaque source string: integer index, rtsp://… URL, or file path.",
    )
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
