import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeRead
from app.services.employee_service import EmployeeService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db)) -> EmployeeService:
    return EmployeeService(db)


@router.post("/", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    svc: EmployeeService = Depends(_svc),
):
    return await svc.create(payload)


@router.get("/", response_model=list[EmployeeRead])
async def list_employees(
    active_only: bool = False,
    svc: EmployeeService = Depends(_svc),
):
    employees = await svc.list_all(active_only=active_only)
    # Annotate has_face_embedding
    result = []
    for emp in employees:
        data = EmployeeRead.model_validate(emp)
        data.has_face_embedding = emp.face_embedding is not None
        result.append(data)
    return result


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    svc: EmployeeService = Depends(_svc),
):
    emp = await svc.get_or_404(employee_id)
    data = EmployeeRead.model_validate(emp)
    data.has_face_embedding = emp.face_embedding is not None
    return data


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    svc: EmployeeService = Depends(_svc),
):
    emp = await svc.update(employee_id, payload)
    data = EmployeeRead.model_validate(emp)
    data.has_face_embedding = emp.face_embedding is not None
    return data


@router.post("/{employee_id}/face", response_model=EmployeeRead)
async def upload_face_image(
    employee_id: uuid.UUID,
    file: UploadFile = File(...),
    svc: EmployeeService = Depends(_svc),
):
    """
    Upload a face reference photo. The system will extract the embedding
    automatically via the vision pipeline and store it.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    path = await svc.save_face_image(employee_id, file)

    # Trigger embedding extraction (inline for MVP — heavy; in production move to worker)
    try:
        from vision.recognizer import FaceRecognizer
        recognizer = FaceRecognizer()
        embedding = recognizer.embed_from_file(path)
        if embedding:
            await svc.update_embedding(employee_id, embedding)
    except Exception as exc:
        # Don't fail the upload — image is saved, embedding can be retried
        pass

    emp = await svc.get_or_404(employee_id)
    data = EmployeeRead.model_validate(emp)
    data.has_face_embedding = emp.face_embedding is not None
    return data


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: uuid.UUID,
    svc: EmployeeService = Depends(_svc),
):
    await svc.delete(employee_id)
