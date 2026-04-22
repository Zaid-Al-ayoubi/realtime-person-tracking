"""
Smoke check — imports every app module and prints a pass/fail report.

Run after `pip install -r requirements.txt`:
    python scripts/smoke_check.py

Exits 0 on success, 1 on any import failure. No database required.
"""
from __future__ import annotations

import importlib
import sys

MODULES = [
    "app",
    "app.core.config",
    "app.core.logging",
    "app.database.session",
    "app.models",
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
    "app.vision.detection",
    "app.vision.tracking",
    "app.vision.tracking.iou_tracker",
    "app.vision.face",
    "app.vision.events",
    "app.vision.events.fire",
    "app.vision.events.violence",
    "app.vision.pipeline",
    "app.workers.batch_processor",
    "app.workers.incident_recorder",
    "app.workers.scheduler",
    "app.api.deps",
    "app.api.v1.router",
    "app.main",
]


def main() -> int:
    failures: list[tuple[str, str]] = []
    for name in MODULES:
        try:
            importlib.import_module(name)
            print(f"  OK   {name}")
        except Exception as exc:
            print(f"  FAIL {name}  ->  {exc!r}")
            failures.append((name, repr(exc)))

    print("-" * 60)
    if failures:
        print(f"FAILED: {len(failures)} module(s) could not be imported.")
        return 1
    print(f"PASSED: {len(MODULES)} modules imported cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
