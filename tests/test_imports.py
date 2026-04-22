"""
Smoke test — every app module must import without side effects.

Does NOT require a live database or any vision extras. The vision
modules lazy-import heavy deps, so they all import under `from x import y`
contracts alone.
"""
from __future__ import annotations

import importlib

MODULES = [
    "app",
    "app.core.config",
    "app.core.logging",
    "app.database.session",
    "app.models",
    "app.models.base",
    "app.models.camera",
    "app.models.employee",
    "app.models.customer",
    "app.models.unknown_candidate",
    "app.models.visit",
    "app.models.detection_log",
    "app.models.incident",
    "app.models.face_embedding",
    "app.schemas.common",
    "app.schemas.camera",
    "app.schemas.employee",
    "app.schemas.customer",
    "app.schemas.visit",
    "app.schemas.incident",
    "app.repositories.base",
    "app.repositories.camera_repository",
    "app.repositories.employee_repository",
    "app.repositories.customer_repository",
    "app.repositories.unknown_candidate_repository",
    "app.repositories.visit_repository",
    "app.repositories.incident_repository",
    "app.repositories.face_embedding_repository",
    "app.services.identity_service",
    "app.services.visit_service",
    "app.services.incident_service",
    "app.services.analytics_service",
    "app.vision.capture",
    "app.vision.capture.base",
    "app.vision.detection",
    "app.vision.detection.base",
    "app.vision.tracking",
    "app.vision.tracking.base",
    "app.vision.tracking.iou_tracker",
    "app.vision.face",
    "app.vision.face.detector",
    "app.vision.face.embedder",
    "app.vision.face.matcher",
    "app.vision.events",
    "app.vision.events.base",
    "app.vision.events.fire",
    "app.vision.events.violence",
    "app.vision.pipeline",
    "app.workers.batch_processor",
    "app.workers.incident_recorder",
    "app.workers.scheduler",
    "app.api.deps",
    "app.api.v1.health",
    "app.api.v1.cameras",
    "app.api.v1.employees",
    "app.api.v1.customers",
    "app.api.v1.visits",
    "app.api.v1.incidents",
    "app.api.v1.analytics",
    "app.api.v1.router",
    "app.main",
]


def test_all_modules_import():
    failures = []
    for name in MODULES:
        try:
            importlib.import_module(name)
        except Exception as exc:
            failures.append((name, repr(exc)))
    assert not failures, f"import failures: {failures}"
