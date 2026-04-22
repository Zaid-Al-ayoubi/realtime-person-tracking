import uuid
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models.mixins import TimestampMixin


class Camera(Base, TimestampMixin):
    """
    Represents a physical camera. `source` can be a device index (e.g. "0"),
    RTSP URL, or file path for batch processing.
    `branch` allows grouping cameras by location/store for multi-branch setups.
    """

    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(500), nullable=False)  # RTSP/device/file
    location: Mapped[str | None] = mapped_column(String(255))
    branch: Mapped[str | None] = mapped_column(String(100), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="camera")  # noqa: F821
    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="camera")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Camera id={self.id} name={self.name!r} source={self.source!r}>"
