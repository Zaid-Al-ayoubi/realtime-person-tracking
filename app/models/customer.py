import uuid
from sqlalchemy import String, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, FLOAT

from app.database import Base
from app.models.mixins import TimestampMixin


class Customer(Base, TimestampMixin):
    """
    A customer profile. Starts as an unknown visitor; promoted to recurring
    once visit_count reaches the configured threshold.

    face_embedding is set the first time a stable face is captured.
    Subsequent appearances are matched against this embedding.
    """

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Optional — manager can label a recurring customer
    name: Mapped[str | None] = mapped_column(String(255))

    # Face data
    face_embedding: Mapped[list[float] | None] = mapped_column(ARRAY(FLOAT))
    face_image_path: Mapped[str | None] = mapped_column(String(500))

    visit_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    visits: Mapped[list["Visit"]] = relationship(  # noqa: F821
        "Visit", back_populates="customer", foreign_keys="Visit.customer_id"
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} recurring={self.is_recurring} visits={self.visit_count}>"
