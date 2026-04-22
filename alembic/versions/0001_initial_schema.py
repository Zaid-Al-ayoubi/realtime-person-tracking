"""Initial schema — all core tables

Revision ID: 0001
Revises:
Create Date: 2026-04-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- employees ---
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100)),
        sa.Column("employee_code", sa.String(50), unique=True),
        sa.Column("face_embedding", postgresql.ARRAY(sa.Float())),
        sa.Column("face_image_path", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_employees_name", "employees", ["name"])
    op.create_index("ix_employees_employee_code", "employees", ["employee_code"])

    # --- customers ---
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("face_embedding", postgresql.ARRAY(sa.Float())),
        sa.Column("face_image_path", sa.String(500)),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- cameras ---
    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("branch", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cameras_branch", "cameras", ["branch"])

    # --- visits ---
    op.create_table(
        "visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_type", sa.String(20), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="SET NULL")),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL")),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id", ondelete="SET NULL")),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("track_id", sa.String(100)),
        sa.Column("session_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_visits_visit_date", "visits", ["visit_date"])
    op.create_index("ix_visits_person_type", "visits", ["person_type"])
    op.create_index("ix_visits_employee_id", "visits", ["employee_id"])
    op.create_index("ix_visits_customer_id", "visits", ["customer_id"])
    op.create_index("ix_visits_session_id", "visits", ["session_id"])

    # --- detection_logs ---
    op.create_table(
        "detection_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("visits.id", ondelete="SET NULL")),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id", ondelete="SET NULL")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("track_id", sa.String(100)),
        sa.Column("person_type", sa.String(20)),
        sa.Column("confidence", sa.Float()),
        sa.Column("face_detected", sa.Boolean()),
        sa.Column("face_confidence", sa.Float()),
        sa.Column("bbox", postgresql.JSONB()),
    )
    op.create_index("ix_detection_logs_timestamp", "detection_logs", ["timestamp"])
    op.create_index("ix_detection_logs_track_id", "detection_logs", ["track_id"])

    # --- incidents ---
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id", ondelete="SET NULL")),
        sa.Column("incident_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("video_clip_path", sa.String(500)),
        sa.Column("video_pre_event_path", sa.String(500)),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_incidents_incident_type", "incidents", ["incident_type"])
    op.create_index("ix_incidents_occurred_at", "incidents", ["occurred_at"])
    op.create_index("ix_incidents_status", "incidents", ["status"])


def downgrade() -> None:
    op.drop_table("incidents")
    op.drop_table("detection_logs")
    op.drop_table("visits")
    op.drop_table("cameras")
    op.drop_table("customers")
    op.drop_table("employees")
