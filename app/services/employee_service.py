"""
Employee service — manages registration, face embedding upload, and basic queries.
Face embedding extraction happens in the vision layer; this service only stores
the result and serves it for recognition.
"""
import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError, ConflictError
from app.models.employee import Employee
from app.repositories.employee_repo import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = EmployeeRepository(session)

    async def create(self, payload: EmployeeCreate) -> Employee:
        if payload.employee_code:
            existing = await self.repo.get_by_code(payload.employee_code)
            if existing:
                raise ConflictError(f"Employee code '{payload.employee_code}' already exists.")
        employee = Employee(**payload.model_dump())
        return await self.repo.create(employee)

    async def get_or_404(self, employee_id: uuid.UUID) -> Employee:
        employee = await self.repo.get(employee_id)
        if not employee:
            raise NotFoundError("Employee", str(employee_id))
        return employee

    async def list_all(self, *, active_only: bool = False) -> list[Employee]:
        if active_only:
            return await self.repo.list_active()
        return await self.repo.list()

    async def update(self, employee_id: uuid.UUID, payload: EmployeeUpdate) -> Employee:
        employee = await self.get_or_404(employee_id)
        data = payload.model_dump(exclude_unset=True)
        for key, val in data.items():
            setattr(employee, key, val)
        return employee

    async def save_face_image(
        self, employee_id: uuid.UUID, file: UploadFile
    ) -> str:
        """
        Persist the uploaded face image and return its path.
        The caller is responsible for extracting the embedding separately
        and calling update_embedding().
        """
        employee = await self.get_or_404(employee_id)
        face_dir = Path(settings.FACE_DB_DIR) / "employees"
        face_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(file.filename or "face.jpg").suffix or ".jpg"
        filename = f"{employee_id}{ext}"
        save_path = face_dir / filename

        async with aiofiles.open(save_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        employee.face_image_path = str(save_path)
        return str(save_path)

    async def update_embedding(
        self, employee_id: uuid.UUID, embedding: list[float]
    ) -> Employee:
        employee = await self.get_or_404(employee_id)
        employee.face_embedding = embedding
        return employee

    async def get_all_with_embeddings(self) -> list[Employee]:
        return await self.repo.get_all_with_embeddings()

    async def delete(self, employee_id: uuid.UUID) -> None:
        deleted = await self.repo.delete(employee_id)
        if not deleted:
            raise NotFoundError("Employee", str(employee_id))
