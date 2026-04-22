from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services.identity_service import IdentityService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
def list_employees(session: Session = Depends(get_db)) -> list[Employee]:
    return EmployeeRepository(session).list()


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, session: Session = Depends(get_db)) -> Employee:
    return EmployeeRepository(session).add(Employee(**payload.model_dump()))


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(employee_id: uuid.UUID, session: Session = Depends(get_db)) -> Employee:
    emp = EmployeeRepository(session).get(employee_id)
    if emp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="employee not found")
    return emp


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: uuid.UUID, payload: EmployeeUpdate, session: Session = Depends(get_db)
) -> Employee:
    emp = EmployeeRepository(session).get(employee_id)
    if emp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="employee not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(emp, key, value)
    return emp


@router.post("/{employee_id}/enroll", response_model=EmployeeRead)
def enroll_face(
    employee_id: uuid.UUID,
    file: UploadFile = File(..., description="Face photo (JPEG/PNG, frontal, clear lighting)"),
    session: Session = Depends(get_db),
) -> Employee:
    """
    Upload a face photo and extract + store the ArcFace embedding.

    Requires vision extras (insightface + onnxruntime) to be installed.
    The endpoint is intentionally synchronous — for a busy deployment,
    move the embedding extraction to a background worker in Phase 2.
    """
    emp = EmployeeRepository(session).get(employee_id)
    if emp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="employee not found")

    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="file must be an image")

    try:
        import cv2
        import numpy as np
        from app.vision.face.embedder import InsightFaceEmbedder
    except (ImportError, RuntimeError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"vision extras not available: {exc}",
        )

    raw = file.file.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="could not decode image")

    embedder = InsightFaceEmbedder()
    embedding = embedder.embed(image)
    if not embedding:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="no face detected in the image — use a clear frontal photo",
        )

    identity = IdentityService(session)
    identity.enroll_employee_face(emp.id, embedding)
    emp.is_enrolled = True
    return emp
