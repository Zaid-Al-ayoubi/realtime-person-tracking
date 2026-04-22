"""
SQLAlchemy engine + session factory.

Sync SQLAlchemy 2.0 style. If/when we move to async we only rewrite this
module and the repositories; the rest of the app depends on abstractions.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_engine() -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        future=True,
    )


engine: Engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
    future=True,
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency + generic context-managed session factory."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
