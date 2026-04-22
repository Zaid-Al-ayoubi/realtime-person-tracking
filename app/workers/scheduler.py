"""
APScheduler-based job runner.

Starts on FastAPI app startup and registers jobs such as:
  * batch chunk processing (every 5 min)
  * idle-visit closer (every 1 min)

Kept small on purpose: Phase 1 registers the closer only. Batch jobs are
registered by the caller at app startup once a Camera row exists.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database.session import SessionLocal
from app.services.visit_service import VisitService

logger = logging.getLogger(__name__)


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(_close_idle_visits, "interval", minutes=1, id="close_idle_visits")
    return scheduler


def _close_idle_visits() -> None:
    session = SessionLocal()
    try:
        count = VisitService(session).close_idle_visits()
        if count:
            session.commit()
    except Exception:  # pragma: no cover
        session.rollback()
        logger.exception("scheduler.close_idle_visits.failed")
    finally:
        session.close()
