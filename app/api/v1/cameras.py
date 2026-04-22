import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.camera import CameraCreate, CameraUpdate, CameraRead
from app.models.camera import Camera
from app.repositories.camera_repo import CameraRepository
from app.core.exceptions import NotFoundError

router = APIRouter()


def _repo(db: AsyncSession = Depends(get_db)) -> CameraRepository:
    return CameraRepository(db)


@router.post("/", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraCreate,
    repo: CameraRepository = Depends(_repo),
):
    camera = Camera(**payload.model_dump())
    return await repo.create(camera)


@router.get("/", response_model=list[CameraRead])
async def list_cameras(
    active_only: bool = False,
    repo: CameraRepository = Depends(_repo),
):
    if active_only:
        return await repo.list_active()
    return await repo.list()


@router.get("/{camera_id}", response_model=CameraRead)
async def get_camera(
    camera_id: uuid.UUID,
    repo: CameraRepository = Depends(_repo),
):
    camera = await repo.get(camera_id)
    if not camera:
        raise NotFoundError("Camera", str(camera_id))
    return camera


@router.patch("/{camera_id}", response_model=CameraRead)
async def update_camera(
    camera_id: uuid.UUID,
    payload: CameraUpdate,
    repo: CameraRepository = Depends(_repo),
):
    camera = await repo.get(camera_id)
    if not camera:
        raise NotFoundError("Camera", str(camera_id))
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(camera, key, val)
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: uuid.UUID,
    repo: CameraRepository = Depends(_repo),
):
    deleted = await repo.delete(camera_id)
    if not deleted:
        raise NotFoundError("Camera", str(camera_id))
