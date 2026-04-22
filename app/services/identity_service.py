"""
Identity resolution service.

This is the single point in the system that decides whether a given face
embedding belongs to:
  * a registered employee,
  * a known recurring customer,
  * an existing unknown candidate (seen before but not promoted), or
  * a brand-new unknown.

It also enforces the promotion rule: unknown candidates become recurring
customers after `settings.unknown_promotion_visits` distinct observations.

The service is deliberately decoupled from any tracker; `track_id` is
irrelevant here. Callers pass an embedding — nothing else.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.customer import Customer
from app.models.face_embedding import FaceEmbedding, FaceOwnerType
from app.models.unknown_candidate import UnknownCandidate
from app.models.visit import EntityType
from app.repositories.customer_repository import CustomerRepository
from app.repositories.face_embedding_repository import FaceEmbeddingRepository
from app.repositories.unknown_candidate_repository import UnknownCandidateRepository

logger = logging.getLogger(__name__)

Embedding = Sequence[float]


@dataclass(frozen=True)
class ResolvedIdentity:
    entity_type: EntityType
    entity_id: uuid.UUID | None
    confidence: float  # 1 - cosine_distance; higher = more similar
    was_promoted: bool = False  # True on the transition unknown -> customer


class IdentityService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._face_repo = FaceEmbeddingRepository(session)
        self._customer_repo = CustomerRepository(session)
        self._unknown_repo = UnknownCandidateRepository(session)

    # ---- public API -----------------------------------------------------

    def resolve(self, embedding: Embedding, *, now: datetime | None = None) -> ResolvedIdentity:
        """Resolve an embedding to a persistent identity, creating or promoting as needed."""
        now = now or datetime.now(timezone.utc)

        best = self._best_match(embedding)
        if best is None:
            # No face embeddings in DB yet → start as unknown candidate.
            candidate = self._create_unknown(embedding, now=now)
            return ResolvedIdentity(
                entity_type=EntityType.unknown,
                entity_id=candidate.id,
                confidence=0.0,
            )

        match_fe, similarity = best
        threshold_similarity = 1.0 - settings.face_match_threshold

        if similarity < threshold_similarity:
            # Close to nothing known — treat as new unknown candidate.
            candidate = self._create_unknown(embedding, now=now)
            return ResolvedIdentity(
                entity_type=EntityType.unknown,
                entity_id=candidate.id,
                confidence=similarity,
            )

        # Matched an existing face. Route based on its owner type.
        if match_fe.owner_type == FaceOwnerType.employee:
            return ResolvedIdentity(
                entity_type=EntityType.employee,
                entity_id=match_fe.owner_id,
                confidence=similarity,
            )

        if match_fe.owner_type == FaceOwnerType.customer:
            customer = self._customer_repo.get(match_fe.owner_id)
            if customer is not None:
                customer.visit_count += 1
                customer.last_seen_at = now
                if customer.first_seen_at is None:
                    customer.first_seen_at = now
            return ResolvedIdentity(
                entity_type=EntityType.customer,
                entity_id=match_fe.owner_id,
                confidence=similarity,
            )

        # FaceOwnerType.unknown_candidate → maybe promote.
        candidate = self._unknown_repo.get(match_fe.owner_id)
        if candidate is None:
            # Embedding points to a deleted candidate; fall through to new unknown.
            new_candidate = self._create_unknown(embedding, now=now)
            return ResolvedIdentity(
                entity_type=EntityType.unknown,
                entity_id=new_candidate.id,
                confidence=similarity,
            )

        candidate.observation_count += 1
        candidate.last_seen_at = now

        if candidate.observation_count >= settings.unknown_promotion_visits:
            customer = self._promote(candidate, now=now)
            return ResolvedIdentity(
                entity_type=EntityType.customer,
                entity_id=customer.id,
                confidence=similarity,
                was_promoted=True,
            )

        return ResolvedIdentity(
            entity_type=EntityType.unknown,
            entity_id=candidate.id,
            confidence=similarity,
        )

    def enroll_employee_face(
        self, employee_id: uuid.UUID, embedding: Embedding, *, quality_score: float | None = None
    ) -> FaceEmbedding:
        """Register a new face embedding for an existing employee."""
        fe = FaceEmbedding(
            owner_type=FaceOwnerType.employee,
            owner_id=employee_id,
            embedding=list(embedding),
            quality_score=quality_score,
        )
        return self._face_repo.add(fe)

    # ---- internals ------------------------------------------------------

    def _best_match(self, embedding: Embedding) -> tuple[FaceEmbedding, float] | None:
        """
        Brute-force cosine similarity over all stored embeddings.

        When pgvector is available we should push this to SQL; keeping it in
        Python here keeps the service portable and MVP-friendly. Swap in an
        ANN query in Phase 2 if/when embedding count grows.
        """
        all_faces = self._face_repo.list_all()
        if not all_faces:
            return None

        query_vec = list(embedding)
        query_norm = _norm(query_vec)
        if query_norm == 0.0:
            return None

        best_fe: FaceEmbedding | None = None
        best_sim = -1.0
        for fe in all_faces:
            stored = list(fe.embedding)
            if len(stored) != len(query_vec):
                continue
            denom = query_norm * _norm(stored)
            if denom == 0.0:
                continue
            sim = _dot(query_vec, stored) / denom
            if sim > best_sim:
                best_sim = sim
                best_fe = fe

        if best_fe is None:
            return None
        return best_fe, best_sim

    def _create_unknown(self, embedding: Embedding, *, now: datetime) -> UnknownCandidate:
        candidate = UnknownCandidate(
            observation_count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        self._unknown_repo.add(candidate)

        fe = FaceEmbedding(
            owner_type=FaceOwnerType.unknown_candidate,
            owner_id=candidate.id,
            embedding=list(embedding),
        )
        self._face_repo.add(fe)
        logger.info("identity.unknown.created", extra={"candidate_id": str(candidate.id)})
        return candidate

    def _promote(self, candidate: UnknownCandidate, *, now: datetime) -> Customer:
        customer = Customer(
            visit_count=candidate.observation_count,
            first_seen_at=candidate.first_seen_at,
            last_seen_at=now,
        )
        self._customer_repo.add(customer)

        # Re-point all embeddings from the candidate to the new customer.
        embeddings = self._face_repo.list_by_owner(
            owner_type=FaceOwnerType.unknown_candidate, owner_id=candidate.id
        )
        for fe in embeddings:
            fe.owner_type = FaceOwnerType.customer
            fe.owner_id = customer.id

        self._unknown_repo.delete(candidate)
        logger.info(
            "identity.unknown.promoted",
            extra={"customer_id": str(customer.id), "visits": customer.visit_count},
        )
        return customer


# ---- vector math (no numpy dependency so tests/skeleton stay light) ----


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: Sequence[float]) -> float:
    return sum(x * x for x in v) ** 0.5
