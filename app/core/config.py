"""
Application configuration.

All runtime knobs come from environment variables or a local .env file.
Accessed everywhere as `from app.core.config import settings`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Application ----
    app_env: Literal["dev", "staging", "prod"] = Field(default="dev", alias="APP_ENV")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    app_log_json: bool = Field(default=False, alias="APP_LOG_JSON")

    # ---- PostgreSQL ----
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="store_analytics", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")

    # ---- Identity / vision ----
    face_match_threshold: float = Field(default=0.45, alias="FACE_MATCH_THRESHOLD")
    unknown_promotion_visits: int = Field(default=2, alias="UNKNOWN_PROMOTION_VISITS")
    visit_idle_timeout_seconds: int = Field(default=300, alias="VISIT_IDLE_TIMEOUT_SECONDS")

    # ---- Incident recorder ----
    incident_pre_roll_seconds: int = Field(default=900, alias="INCIDENT_PRE_ROLL_SECONDS")
    incident_post_roll_seconds: int = Field(default=120, alias="INCIDENT_POST_ROLL_SECONDS")
    incident_clip_dir: Path = Field(default=Path("./data/incidents"), alias="INCIDENT_CLIP_DIR")

    # ---- Storage ----
    media_root: Path = Field(default=Path("./data/media"), alias="MEDIA_ROOT")
    video_chunk_dir: Path = Field(default=Path("./data/chunks"), alias="VIDEO_CHUNK_DIR")

    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        """SQLAlchemy DSN. Uses psycopg3 driver."""
        dsn = PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )
        return str(dsn)

    @computed_field  # type: ignore[misc]
    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
