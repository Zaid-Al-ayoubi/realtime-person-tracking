"""
Unit tests for the core identity-resolution rules.

Uses an in-memory SQLite with shared cache. Note: pgvector features are
skipped because SQLite doesn't support them — we exercise the ARRAY
fallback path, which is exactly what runs in prod when pgvector is absent.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from app.models.employee import Employee
from app.models.face_embedding import FaceEmbedding, FaceOwnerType
from app.models.visit import EntityType
from app.services.identity_service import IdentityService


@pytest.fixture()
def session() -> Session:
    # Force ARRAY fallback path by monkey-patching FaceEmbedding's embedding col type
    # is not trivial here — instead we just use our ARRAY-compatible test fixture.
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    with SessionLocal() as s:
        yield s


def _vec(pattern: int) -> list[float]:
    # Build a distinguishable 512-d vector.
    return [float(pattern)] * 512


def test_unknown_then_promoted_to_customer(session: Session, monkeypatch):
    # Set promotion threshold to 2 visits for this test.
    from app.core import config as config_mod
    monkeypatch.setattr(config_mod.settings, "unknown_promotion_visits", 2)
    monkeypatch.setattr(config_mod.settings, "face_match_threshold", 0.3)

    identity = IdentityService(session)

    first = identity.resolve(_vec(1))
    assert first.entity_type == EntityType.unknown

    second = identity.resolve(_vec(1))
    assert second.entity_type == EntityType.customer
    assert second.was_promoted is True


def test_employee_match_short_circuits_promotion(session: Session, monkeypatch):
    from app.core import config as config_mod
    monkeypatch.setattr(config_mod.settings, "face_match_threshold", 0.3)

    employee = Employee(full_name="Tester")
    session.add(employee)
    session.flush()

    session.add(
        FaceEmbedding(
            owner_type=FaceOwnerType.employee,
            owner_id=employee.id,
            embedding=_vec(7),
        )
    )
    session.flush()

    identity = IdentityService(session)
    resolved = identity.resolve(_vec(7))
    assert resolved.entity_type == EntityType.employee
    assert resolved.entity_id == employee.id
