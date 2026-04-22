"""Initial schema — all core tables

Revision ID: 0001
Revises:
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Enums
    # ------------------------------------------------------------------ #
    employee_status = postgresql.ENUM(
        "active", "inactive", "terminated", name="employee_status", create_type=False
    )
    employee_status.create(op.get_bind(), checkfirst=True)

    face_owner_type = postgresql.ENUM(
        "employee", "customer", "unknown_candidate", name="face_owner_type", create_type=False
    )
    face_owner_type.create(op.get_bind(), checkfirst=True)

    entity_type = postgresql.ENUM(
        "employee", "customer", "unknown", name="entity_type", create_type=False
    )
    entity_type.create(op.get_bind(), checkfirst=True)

    incident_type = postgresql.ENUM(
        "fire", "fight", "violence", "suspicious", "emergency", "other",
        name="incident_type", create_type=False
    )
    incident_type.create(op.get_bind(), checkfirst=True)

    incident_severity = postgresql.ENUM(
        "low", "medium", "high", "critical", name="incident_severity", create_type=False
    )
    incident_severity.create(op.get_bind(), checkfirst=True)

    incident_status = postgresql.ENUM(
        "open", "acknowledged", "resolved", "dismissed",
        name="incident_status", create_type=False
    )
    incident_status.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------ #
    # cameras
    # ------------------------------------------------------------------ #
    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # employees
    # ------------------------------------------------------------------ #
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("role", sa.String(128), nullable=True),
        sa.Column("external_ref", sa.String(128), nullable=True, unique=True),
        sa.Column(
            "status",
            postgresql.ENUM("active", "inactive", "terminated", name="employee_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("is_enrolled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # customers
    # ------------------------------------------------------------------ #
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("display_name", sa.String(256), nullable=True),
        sa.Column("visit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # unknown_candidates  — staging identity before promotion to Customer
    # ------------------------------------------------------------------ #
    op.create_table(
        "unknown_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("observation_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ------------------------------------------------------------------ #
    # face_embeddings  — polymorphic: employee / customer / unknown_candidate
    # ------------------------------------------------------------------ #
    op.create_table(
        "face_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "owner_type",
            postgresql.ENUM("employee", "customer", "unknown_candidate", name="face_owner_type"),
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Store as ARRAY(Float) — pgvector ivfflat index added in a later migration
        sa.Column("embedding", postgresql.ARRAY(sa.Float), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_face_embeddings_owner", "face_embeddings", ["owner_type", "owner_id"])

    # ------------------------------------------------------------------ #
    # visits
    # ------------------------------------------------------------------ #
    op.create_table(
        "visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "entity_type",
            postgresql.ENUM("employee", "customer", "unknown", name="entity_type"),
            nullable=False,
        ),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_visits_entity", "visits", ["entity_type", "entity_id"])
    op.create_index("ix_visits_started_at", "visits", ["started_at"])

    # ------------------------------------------------------------------ #
    # detection_logs
    # ------------------------------------------------------------------ #
    op.create_table(
        "detection_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("visits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("track_id", sa.Integer, nullable=True),
        sa.Column("bbox_x", sa.Float, nullable=False),
        sa.Column("bbox_y", sa.Float, nullable=False),
        sa.Column("bbox_w", sa.Float, nullable=False),
        sa.Column("bbox_h", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("resolved_entity_type", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_detection_logs_captured_at", "detection_logs", ["captured_at"])

    # ------------------------------------------------------------------ #
    # incidents
    # ------------------------------------------------------------------ #
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "type",
            postgresql.ENUM("fire", "fight", "violence", "suspicious", "emergency", "other",
                            name="incident_type"),
            nullable=False,
        ),
        sa.Column(
            "severity",
            postgresql.ENUM("low", "medium", "high", "critical", name="incident_severity"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status",
            postgresql.ENUM("open", "acknowledged", "resolved", "dismissed",
                            name="incident_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("clip_path", sa.String(512), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_incidents_detected_at", "incidents", ["detected_at"])
    op.create_index("ix_incidents_status", "incidents", ["status"])


def downgrade() -> None:
    op.drop_table("incidents")
    op.drop_table("detection_logs")
    op.drop_table("visits")
    op.drop_table("face_embeddings")
    op.drop_table("unknown_candidates")
    op.drop_table("customers")
    op.drop_table("employees")
    op.drop_table("cameras")

    op.execute("DROP TYPE IF EXISTS incident_status")
    op.execute("DROP TYPE IF EXISTS incident_severity")
    op.execute("DROP TYPE IF EXISTS incident_type")
    op.execute("DROP TYPE IF EXISTS entity_type")
    op.execute("DROP TYPE IF EXISTS face_owner_type")
    op.execute("DROP TYPE IF EXISTS employee_status")
