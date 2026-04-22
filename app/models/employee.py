import uuid
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, FLOAT

from app.database import Base
from app.models.mixins import TimestampMixin


class Employee(Base, TimestampMixin):
    """
    Registered store employee. Face embedding is used for recognition at entry.
    visit_sessions are kept separate so we can compute daily attendance durations.
    """

    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(100))
    employee_code: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)

    # Face data — embedding stored as float array; face_image_path points to the reference photo
    face_embedding: Mapped[list[float] | None] = mapped_column(ARRAY(FLOAT))
    face_image_path: Mapped[str | None] = mapped_column(String(500))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    visits: Mapped[list["Visit"]] = relationship(  # noqa: F821
        "Visit", back_populates="employee", foreign_keys="Visit.employee_id"
    )

    def __repr__(self) -> str:
        return f"<Employee id={self.id} name={self.name!r}>"
