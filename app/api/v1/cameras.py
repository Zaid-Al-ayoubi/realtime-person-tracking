from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.camera import Camera
from app.repositories.camera_repository import CameraRepository
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraRead])
def list_cameras(session: Session = Depends(get_db)) -> list[Camera]:
    return CameraRepository(session).list()


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate, session: Session = Depends(get_db)) -> Camera:
    repo = CameraRepository(session)
    if repo.get_by_name(payload.name) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="camera name already exists")
    return repo.add(Camera(**payload.model_dump()))


@router.get("/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: uuid.UUID, session: Session = Depends(get_db)) -> Camera:
    camera = CameraRepository(session).get(camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="camera not found")
    return camera


@router.patch("/{camera_id}", response_model=CameraRead)
def update_camera(
    camera_id: uuid.UUID, payload: CameraUpdate, session: Session = Depends(get_db)
) -> Camera:
    camera = CameraRepository(session).get(camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="camera not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, key, value)
    return camera
