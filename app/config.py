from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Store Analytics"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://analytics:analytics@localhost:5432/store_analytics"
    DATABASE_URL_SYNC: str = "postgresql://analytics:analytics@localhost:5432/store_analytics"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "changeme-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Vision model paths
    PERSON_MODEL_PATH: str = "models/yolov8m.pt"
    FACE_MODEL_PATH: str = "models/face_yolov8s.pt"
    PERSON_CONF_THRESHOLD: float = 0.4
    FACE_CONF_THRESHOLD: float = 0.4
    FACE_STABILITY_FRAMES: int = 3

    # Identity resolution
    FACE_SIMILARITY_THRESHOLD: float = 0.55
    RECURRING_CUSTOMER_MIN_VISITS: int = 2

    # Storage
    RECORDINGS_DIR: str = "recordings"
    FACE_DB_DIR: str = "face_db"
    PRE_EVENT_BUFFER_SECONDS: int = 900   # 15 minutes
    POST_EVENT_RECORD_SECONDS: int = 300  # 5 minutes

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
