"""
Face embeddings — the DB-side of identity resolution.

Uses pgvector if the extension is installed; otherwise falls back to
ARRAY(Float). The matcher layer hides the difference.

A single person (employee or customer) can have many embeddings — we
enroll multiple angles / lighting conditions over time and match against
the best one.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum, Float, Index
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin

try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import-not-found]
    _HAS_PGVECTOR = True
except ImportError:  # pragma: no cover — fallback path
    _HAS_PGVECTOR = False


EMBEDDING_DIM = 512  # InsightFace ArcFace default


class FaceOwnerType(str, enum.Enum):
    employee = "employee"
    customer = "customer"
    unknown_candidate = "unknown_candidate"


def _embedding_column():
    if _HAS_PGVECTOR:
        return mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    return mapped_column(ARRAY(Float), nullable=False)


class FaceEmbedding(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "face_embeddings"

    owner_type: Mapped[FaceOwnerType] = mapped_column(
        SAEnum(FaceOwnerType, name="face_owner_type"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        doc="FK is polymorphic by owner_type; not enforced at DB level.",
    )
    embedding = _embedding_column()
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_face_embeddings_owner", "owner_type", "owner_id"),
    )

# pgvector ANN index — only meaningful when pgvector is installed.
# Alembic migrations will CREATE INDEX ... USING ivfflat ... on this column.
# We don't declare it here because ivfflat requires post-population tuning.
