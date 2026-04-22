"""
Register an employee and enroll one or more face images.

Usage:
    python scripts/register_employee.py --name "Ahmed" --role "Cashier" \
           --image path/to/face1.jpg [--image path/to/face2.jpg ...]
"""
from __future__ import annotations

import argparse
import logging

from app.core.logging import configure_logging
from app.database.session import SessionLocal
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.services.identity_service import IdentityService

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", default=None)
    parser.add_argument("--external-ref", default=None)
    parser.add_argument("--image", action="append", default=[], help="Path to a face image (repeatable)")
    args = parser.parse_args()

    configure_logging()

    try:
        import cv2

        from app.vision.face.embedder import InsightFaceEmbedder
    except Exception as exc:
        raise SystemExit(f"Vision extras required: {exc}")

    embedder = InsightFaceEmbedder()

    session = SessionLocal()
    try:
        emp = EmployeeRepository(session).add(
            Employee(full_name=args.name, role=args.role, external_ref=args.external_ref)
        )
        session.flush()

        identity = IdentityService(session)
        enrolled = 0
        for path in args.image:
            image = cv2.imread(path)
            if image is None:
                logger.warning("skip_unreadable", extra={"path": path})
                continue
            embedding = embedder.embed(image)
            if not embedding:
                logger.warning("no_face_found", extra={"path": path})
                continue
            identity.enroll_employee_face(emp.id, embedding)
            enrolled += 1

        if enrolled:
            emp.is_enrolled = True
        session.commit()
        print(f"Registered employee {emp.id} with {enrolled} face(s).")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
