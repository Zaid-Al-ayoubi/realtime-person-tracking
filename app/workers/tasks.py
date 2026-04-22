"""
Celery tasks for background video processing.

process_video_segment — the core batch task:
  1. Runs the full vision pipeline on a recorded video file
  2. Resolves identities against the DB (using sync session)
  3. Opens and closes Visit records
  4. Creates Incident records if events are detected

All DB access here uses a synchronous SQLAlchemy session
(psycopg2 driver) because Celery workers are sync processes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

# Synchronous engine for Celery workers
_sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_pre_ping=True,
    pool_size=5,
)
SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)


def _get_sync_session() -> Session:
    return SyncSession()


# ---------------------------------------------------------------------------
# Identity resolution helper (sync DB calls)
# ---------------------------------------------------------------------------
def _resolve_and_persist(
    session_id: str,
    identity_payload: dict,
    db: Session,
) -> None:
    """
    Resolve a face embedding against the DB and open/update a Visit.
    Runs inside the Celery worker synchronously.
    """
    import math
    from app.models.employee import Employee
    from app.models.customer import Customer
    from app.models.visit import Visit, PersonType

    embedding: list[float] = identity_payload["embedding"]
    track_id: str = identity_payload["track_id"]
    camera_id_str: str | None = identity_payload.get("camera_id")
    detected_at = datetime.fromisoformat(identity_payload["detected_at"])
    camera_id = uuid.UUID(camera_id_str) if camera_id_str else None

    threshold = settings.FACE_SIMILARITY_THRESHOLD

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0.0

    # 1. Employee match
    employees = db.query(Employee).filter(
        Employee.is_active == True, Employee.face_embedding.is_not(None)
    ).all()

    best_emp, best_emp_sim = None, 0.0
    for emp in employees:
        sim = cosine(embedding, emp.face_embedding)
        if sim > best_emp_sim:
            best_emp_sim, best_emp = sim, emp

    if best_emp and best_emp_sim >= threshold:
        _open_visit_sync(db, PersonType.EMPLOYEE, detected_at, camera_id, session_id, track_id,
                         employee_id=best_emp.id)
        logger.info("worker.matched_employee", name=best_emp.name, sim=round(best_emp_sim, 3))
        return

    # 2. Customer match
    customers = db.query(Customer).filter(Customer.face_embedding.is_not(None)).all()
    best_cust, best_cust_sim = None, 0.0
    for c in customers:
        sim = cosine(embedding, c.face_embedding)
        if sim > best_cust_sim:
            best_cust_sim, best_cust = sim, c

    if best_cust and best_cust_sim >= threshold:
        best_cust.visit_count += 1
        if best_cust.visit_count >= settings.RECURRING_CUSTOMER_MIN_VISITS:
            best_cust.is_recurring = True
        _open_visit_sync(db, PersonType.CUSTOMER, detected_at, camera_id, session_id, track_id,
                         customer_id=best_cust.id)
        logger.info("worker.matched_customer", id=str(best_cust.id), sim=round(best_cust_sim, 3))
        return

    # 3. Unknown — create minimal customer record for future matching
    new_customer = Customer(
        face_embedding=embedding,
        visit_count=1,
        is_recurring=False,
    )
    db.add(new_customer)
    db.flush()
    _open_visit_sync(db, PersonType.UNKNOWN, detected_at, camera_id, session_id, track_id,
                     customer_id=new_customer.id)
    logger.info("worker.new_unknown_visitor", customer_id=str(new_customer.id))


def _open_visit_sync(
    db: Session,
    person_type,
    entry_time: datetime,
    camera_id,
    session_id: str,
    track_id: str,
    employee_id=None,
    customer_id=None,
) -> None:
    from app.models.visit import Visit
    import datetime as dt

    visit = Visit(
        person_type=person_type.value,
        employee_id=employee_id,
        customer_id=customer_id,
        camera_id=camera_id,
        entry_time=entry_time,
        visit_date=entry_time.date(),
        track_id=track_id,
        session_id=session_id,
    )
    db.add(visit)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, name="process_video_segment", max_retries=2)
def process_video_segment(
    self,
    video_path: str,
    camera_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Main batch processing task. Enqueue from the API when a new video
    segment is available (e.g. after a 30-min recording completes).
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    session_id = session_id or uuid.uuid4().hex
    cam_uuid = uuid.UUID(camera_id) if camera_id else None

    logger.info("task.process_video_segment.start", video=video_path, session=session_id)

    db = _get_sync_session()
    collected_identities: list[dict] = []
    collected_incidents: list[dict] = []

    def on_identity(sid: str, payload: dict) -> None:
        collected_identities.append(payload)

    def on_incident(event, pre_path, post_path) -> None:
        collected_incidents.append({
            "type": event.incident_type.value,
            "severity": event.severity.value,
            "confidence": event.confidence,
            "occurred_at": event.detected_at.isoformat(),
            "pre_path": pre_path,
            "post_path": post_path,
        })

    try:
        from vision.pipeline import VisionPipeline
        pipeline = VisionPipeline(
            camera_id=cam_uuid,
            session_id=session_id,
            on_identity=on_identity,
            on_incident=on_incident,
        )
        summary = pipeline.process_video_file(video_path)

        # Persist resolved identities
        for payload in collected_identities:
            try:
                _resolve_and_persist(session_id, payload, db)
            except Exception as exc:
                logger.error("task.identity_persist_error", error=str(exc))

        # Persist incidents
        from app.models.incident import Incident
        for inc in collected_incidents:
            incident = Incident(
                camera_id=cam_uuid,
                incident_type=inc["type"],
                severity=inc["severity"],
                confidence=inc["confidence"],
                occurred_at=datetime.fromisoformat(inc["occurred_at"]),
                video_pre_event_path=inc.get("pre_path"),
                video_clip_path=inc.get("post_path"),
            )
            db.add(incident)

        # Close any visits still open at end of segment
        from app.models.visit import Visit
        end_time = datetime.now(timezone.utc)
        open_visits = db.query(Visit).filter(
            Visit.session_id == session_id,
            Visit.exit_time.is_(None),
        ).all()
        for v in open_visits:
            v.close(end_time)

        db.commit()
        logger.info("task.process_video_segment.done", session=session_id, **summary)
        return {"session_id": session_id, **summary, "incidents": len(collected_incidents)}

    except Exception as exc:
        db.rollback()
        logger.error("task.process_video_segment.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
