"""
Identity resolution service.

Bridges the vision layer and the database:
  - Receives a face embedding from the vision pipeline
  - Tries to match against employees first, then known customers
  - If no match: creates or updates an unknown-visitor accumulator
  - Promotes unknown visitors to Customer profiles after N appearances

Architecture note:
  - track_id is TEMPORARY (valid only within one processing session)
  - DB identity (employee_id / customer_id / UUID) is PERSISTENT

This service is called from the batch processor (worker) and can
also be called from a real-time handler.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.models.employee import Employee
from app.models.customer import Customer
from app.models.visit import PersonType
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.customer_repo import CustomerRepository
from app.services.customer_service import CustomerService
from app.services.visit_service import VisitService
from app.schemas.visit import VisitCreate

logger = get_logger(__name__)


class ResolvedType(str, Enum):
    EMPLOYEE = "employee"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


@dataclass
class ResolvedIdentity:
    resolved_type: ResolvedType
    employee: Optional[Employee] = None
    customer: Optional[Customer] = None
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# In-memory accumulator for unknown visitors (per-process, reset on restart)
# For multi-process setups this should move to Redis.
# ---------------------------------------------------------------------------
@dataclass
class _UnknownAccumulator:
    temp_id: str          # arbitrary key (e.g. "unknown_<uuid>")
    embedding: list[float]
    appearance_count: int = 1
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    customer_id: Optional[uuid.UUID] = None  # set once promoted


_unknown_store: dict[str, _UnknownAccumulator] = {}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _best_match(
    embedding: list[float],
    candidates: list[tuple[uuid.UUID, list[float]]],
    threshold: float,
) -> tuple[uuid.UUID | None, float]:
    """Return (id, similarity) of the best candidate above threshold, else (None, 0)."""
    best_id, best_sim = None, 0.0
    for cid, emb in candidates:
        sim = _cosine_similarity(embedding, emb)
        if sim > best_sim:
            best_sim = sim
            best_id = cid
    if best_sim >= threshold:
        return best_id, best_sim
    return None, best_sim


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.emp_repo = EmployeeRepository(session)
        self.cust_repo = CustomerRepository(session)
        self.cust_service = CustomerService(session)
        self.visit_service = VisitService(session)
        self.threshold = settings.FACE_SIMILARITY_THRESHOLD

    # ------------------------------------------------------------------
    # Primary entry point called by the vision worker per detected face
    # ------------------------------------------------------------------
    async def resolve(
        self,
        embedding: list[float],
        *,
        camera_id: uuid.UUID | None,
        session_id: str,
        track_id: str,
        detected_at: datetime,
        face_image_path: str | None = None,
    ) -> ResolvedIdentity:
        """
        1. Try employee match
        2. Try known-customer match
        3. Fall back to unknown accumulator logic
        Returns the resolved identity so the caller can open/update a Visit.
        """
        # --- 1. Employee match ---
        employees = await self.emp_repo.get_all_with_embeddings()
        emp_candidates = [(e.id, e.face_embedding) for e in employees if e.face_embedding]
        emp_id, emp_sim = _best_match(embedding, emp_candidates, self.threshold)
        if emp_id:
            emp = next(e for e in employees if e.id == emp_id)
            logger.info("identity.resolved_employee", name=emp.name, sim=round(emp_sim, 3))
            return ResolvedIdentity(
                resolved_type=ResolvedType.EMPLOYEE, employee=emp, confidence=emp_sim
            )

        # --- 2. Known-customer match ---
        customers = await self.cust_repo.get_all_with_embeddings()
        cust_candidates = [(c.id, c.face_embedding) for c in customers if c.face_embedding]
        cust_id, cust_sim = _best_match(embedding, cust_candidates, self.threshold)
        if cust_id:
            cust = next(c for c in customers if c.id == cust_id)
            logger.info("identity.resolved_customer", id=str(cust_id), sim=round(cust_sim, 3))
            # Update visit count on match
            await self.cust_service.record_new_visit(cust.id)
            return ResolvedIdentity(
                resolved_type=ResolvedType.CUSTOMER, customer=cust, confidence=cust_sim
            )

        # --- 3. Unknown visitor accumulator ---
        identity = await self._handle_unknown(
            embedding, detected_at=detected_at, face_image_path=face_image_path
        )
        return identity

    async def _handle_unknown(
        self,
        embedding: list[float],
        *,
        detected_at: datetime,
        face_image_path: str | None,
    ) -> ResolvedIdentity:
        """
        Match against existing unknown accumulators.
        If match found → increment appearance count, check for promotion.
        If no match → create new accumulator entry.
        """
        threshold = self.threshold

        best_key: str | None = None
        best_sim = 0.0
        for key, acc in _unknown_store.items():
            sim = _cosine_similarity(embedding, acc.embedding)
            if sim > best_sim:
                best_sim = sim
                best_key = key

        if best_key and best_sim >= threshold:
            acc = _unknown_store[best_key]
            acc.appearance_count += 1
            acc.last_seen = detected_at
            logger.info(
                "identity.unknown_returning",
                key=best_key,
                appearances=acc.appearance_count,
                sim=round(best_sim, 3),
            )

            # Promote if threshold reached and not yet promoted
            if (
                acc.appearance_count >= settings.RECURRING_CUSTOMER_MIN_VISITS
                and acc.customer_id is None
            ):
                customer = await self.cust_service.create_unknown_with_embedding(
                    embedding=acc.embedding, image_path=face_image_path
                )
                acc.customer_id = customer.id
                logger.info("identity.promoted_to_customer", customer_id=str(customer.id))
                return ResolvedIdentity(
                    resolved_type=ResolvedType.CUSTOMER,
                    customer=customer,
                    confidence=best_sim,
                )

            if acc.customer_id:
                # Already promoted in a previous cycle
                customer = await self.cust_repo.get(acc.customer_id)
                if customer:
                    await self.cust_service.record_new_visit(customer.id)
                    return ResolvedIdentity(
                        resolved_type=ResolvedType.CUSTOMER,
                        customer=customer,
                        confidence=best_sim,
                    )
        else:
            # New unknown
            key = f"unknown_{uuid.uuid4().hex[:8]}"
            _unknown_store[key] = _UnknownAccumulator(
                temp_id=key, embedding=embedding, first_seen=detected_at, last_seen=detected_at
            )
            logger.info("identity.new_unknown", key=key)

        return ResolvedIdentity(resolved_type=ResolvedType.UNKNOWN, confidence=best_sim)

    # ------------------------------------------------------------------
    # Helper: open a Visit record from a resolved identity
    # ------------------------------------------------------------------
    async def open_visit_for_identity(
        self,
        identity: ResolvedIdentity,
        *,
        camera_id: uuid.UUID | None,
        session_id: str,
        track_id: str,
        entry_time: datetime,
    ) -> None:
        payload = VisitCreate(
            person_type=PersonType(identity.resolved_type.value),
            employee_id=identity.employee.id if identity.employee else None,
            customer_id=identity.customer.id if identity.customer else None,
            camera_id=camera_id,
            entry_time=entry_time,
            visit_date=entry_time.date(),
            track_id=track_id,
            session_id=session_id,
        )
        await self.visit_service.open_visit(payload)
