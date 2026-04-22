"""
Face-embedding repository.

NOTE on similarity search:
- When pgvector is present, the matcher can issue an ANN query directly in SQL
  (`embedding <=> :query_embedding`). This repo exposes a hook for that.
- When pgvector is not present, services fetch the full set and compute cosine
  similarity in Python. That is fine for MVP scale (hundreds of employees,
  a few thousand recurring customers).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.face_embedding import FaceEmbedding, FaceOwnerType
from app.repositories.base import BaseRepository


class FaceEmbeddingRepository(BaseRepository[FaceEmbedding]):
    model = FaceEmbedding

    def list_by_owner(
        self, *, owner_type: FaceOwnerType, owner_id: uuid.UUID
    ) -> list[FaceEmbedding]:
        stmt = select(FaceEmbedding).where(
            FaceEmbedding.owner_type == owner_type,
            FaceEmbedding.owner_id == owner_id,
        )
        return list(self.session.scalars(stmt).all())

    def list_all(self) -> list[FaceEmbedding]:
        stmt = select(FaceEmbedding)
        return list(self.session.scalars(stmt).all())
