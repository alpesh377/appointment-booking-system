"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('ADMIN','PROVIDER','CUSTOMER')", name="ck_users_role"),
    )

    op.create_table(
        "provider_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("bio", sa.Text()),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "duration_minutes >= 15 AND duration_minutes <= 480 AND duration_minutes % 5 = 0",
            name="ck_services_duration",
        ),
    )
    op.create_index("ix_services_provider", "services", ["provider_id"])

    op.create_table(
        "availability_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_availability_weekday"),
        sa.CheckConstraint("start_time < end_time", name="ck_availability_order"),
    )
    op.create_index("ix_availability_rules_provider", "availability_rules", ["provider_id"])

    op.create_table(
        "schedule_breaks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer()),
        sa.Column("on_date", sa.Date()),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.CheckConstraint(
            "(weekday IS NOT NULL AND on_date IS NULL) OR (weekday IS NULL AND on_date IS NOT NULL)",
            name="ck_breaks_kind",
        ),
        sa.CheckConstraint(
            "weekday IS NULL OR (weekday >= 0 AND weekday <= 6)", name="ck_breaks_weekday"
        ),
        sa.CheckConstraint("start_time < end_time", name="ck_breaks_order"),
    )
    op.create_index("ix_schedule_breaks_provider", "schedule_breaks", ["provider_id"])

    op.create_table(
        "date_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.String(300)),
        sa.UniqueConstraint("provider_id", "date", name="uq_override_provider_date"),
    )
    op.create_index("ix_date_overrides_provider", "date_overrides", ["provider_id"])

    op.create_table(
        "date_override_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "override_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("date_overrides.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.CheckConstraint("start_time < end_time", name="ck_override_window_order"),
    )
    op.create_index(
        "ix_date_override_windows_override", "date_override_windows", ["override_id"]
    )

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.Text()),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "rescheduled_from_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "rescheduled_to_id",
            postgresql.UUID(as_uuid=True),
        ),
        sa.Column("cancelled_by_role", sa.String(20)),
        sa.Column(
            "cancelled_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("cancellation_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('PENDING','CONFIRMED','REJECTED','CANCELLED','COMPLETED','EXPIRED','RESCHEDULED')",
            name="ck_appointments_status",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_appointments_order"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_appointments_duration"),
    )
    op.create_index("ix_appointments_provider_start", "appointments", ["provider_id", "starts_at"])
    op.create_index("ix_appointments_customer_start", "appointments", ["customer_id", "starts_at"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_foreign_key(
        "appointments_rescheduled_to_id_fkey",
        "appointments",
        "appointments",
        ["rescheduled_to_id"],
        ["id"],
        ondelete="SET NULL",
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_appointment_one_successor "
        "ON appointments (rescheduled_from_id) WHERE rescheduled_from_id IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE appointments ADD CONSTRAINT appointments_no_overlap "
        "EXCLUDE USING gist (provider_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) "
        "WHERE (status IN ('PENDING','CONFIRMED'))"
    )

    op.create_table(
        "appointment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(20)),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_events_appointment", "appointment_events", ["appointment_id", "created_at"])


def downgrade() -> None:
    op.drop_table("appointment_events")
    op.drop_table("appointments")
    op.drop_table("date_override_windows")
    op.drop_table("date_overrides")
    op.drop_table("schedule_breaks")
    op.drop_table("availability_rules")
    op.drop_table("services")
    op.drop_table("provider_profiles")
    op.drop_table("users")
