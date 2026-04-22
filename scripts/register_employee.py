#!/usr/bin/env python3
"""
CLI tool for registering a new employee with a face photo.

Usage:
    python scripts/register_employee.py \
        --name "Ahmed Ali" \
        --role "Cashier" \
        --code "EMP001" \
        --image face_db/ahmed.jpg

Must be run with the DB running (docker-compose up db).
"""
import argparse
import sys
import uuid
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.employee import Employee


def main() -> None:
    parser = argparse.ArgumentParser(description="Register an employee with face recognition.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", default=None)
    parser.add_argument("--code", default=None, help="Unique employee code (optional)")
    parser.add_argument("--image", required=True, help="Path to face reference image")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    # Extract face embedding
    print(f"[INFO] Extracting face embedding from {image_path}...")
    try:
        from vision.recognizer import FaceRecognizer
        recognizer = FaceRecognizer()
        embedding = recognizer.embed_from_file(str(image_path))
    except Exception as exc:
        print(f"[ERROR] Recognizer failed: {exc}")
        sys.exit(1)

    if embedding is None:
        print("[ERROR] No face detected in the provided image. Use a clear frontal face photo.")
        sys.exit(1)

    print(f"[OK] Embedding extracted ({len(embedding)}-dim)")

    # Copy image to face_db/employees/
    dest_dir = Path(settings.FACE_DB_DIR) / "employees"
    dest_dir.mkdir(parents=True, exist_ok=True)
    emp_id = uuid.uuid4()
    dest_path = dest_dir / f"{emp_id}{image_path.suffix}"
    import shutil
    shutil.copy2(image_path, dest_path)

    # Insert into DB
    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        employee = Employee(
            id=emp_id,
            name=args.name,
            role=args.role,
            employee_code=args.code,
            face_embedding=embedding,
            face_image_path=str(dest_path),
            is_active=True,
        )
        db.add(employee)
        db.commit()
        print(f"[OK] Employee registered successfully.")
        print(f"     ID   : {emp_id}")
        print(f"     Name : {args.name}")
        print(f"     Role : {args.role}")
        print(f"     Code : {args.code}")
        print(f"     Image: {dest_path}")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] DB insert failed: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
