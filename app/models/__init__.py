"""
ORM model registry.

Importing this package imports every model so that SQLAlchemy's metadata is
fully populated before Alembic autogenerate or create_all runs.
"""

from app.models.base import Base
from app.models.camera import Camera
from app.models.employee import Employee
from app.models.customer import Customer
from app.models.unknown_candidate import UnknownCandidate
from app.models.visit import Visit
from app.models.detection_log import DetectionLog
from app.models.incident import Incident
from app.models.face_embedding import FaceEmbedding, FaceOwnerType

__all__ = [
    "Base",
    "Camera",
    "Employee",
    "Customer",
    "UnknownCandidate",
    "Visit",
    "DetectionLog",
    "Incident",
    "FaceEmbedding",
    "FaceOwnerType",
]
