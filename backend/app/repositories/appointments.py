from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutil import utcnow
from app.models import ACTIVE_STATUSES, Appointment, AppointmentEvent, AppointmentStatus


def provider_lock_key(provider_id: uuid.UUID) -> int:
    return int.from_bytes(provider_id.bytes[:8], "big", signed=True)


def acquire_provider_lock(db: Session, provider_id: uuid.UUID) -> None:
    """Take the per-provider transaction-scoped advisory lock.

    Every appointment mutation for a provider takes this lock first, so
    availability reads, bookings and transitions are serialised per provider.
    """
    db.execute(text(f"SET LOCAL lock_timeout = '{int(settings.lock_timeout_ms)}ms'"))
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": provider_lock_key(provider_id)})


def sweep_expired(db: Session, provider_id: uuid.UUID, now: datetime | None = None) -> int:
    """Lazily expire pending requests whose hold deadline has passed."""
    now = now or utcnow()
    rows = (
        db.execute(
            select(Appointment)
            .where(
                Appointment.provider_id == provider_id,
                Appointment.status == AppointmentStatus.PENDING.value,
                Appointment.hold_expires_at.is_not(None),
                Appointment.hold_expires_at <= now,
            )
            .order_by(Appointment.id)
            .with_for_update()
        )
        .scalars()
        .all()
    )
    for appointment in rows:
        appointment.status = AppointmentStatus.EXPIRED.value
        appointment.hold_expires_at = None
        db.add(
            AppointmentEvent(
                appointment_id=appointment.id,
                from_status=AppointmentStatus.PENDING.value,
                to_status=AppointmentStatus.EXPIRED.value,
                actor_user_id=None,
                actor_role="SYSTEM",
                reason="Pending request expired.",
            )
        )
    if rows:
        db.flush()
    return len(rows)


def lock_active_appointments(
    db: Session,
    provider_id: uuid.UUID,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Appointment]:
    stmt = (
        select(Appointment)
        .where(
            Appointment.provider_id == provider_id,
            Appointment.status.in_([s.value for s in ACTIVE_STATUSES]),
        )
        .order_by(Appointment.id)
        .with_for_update()
    )
    if start is not None and end is not None:
        stmt = stmt.where(Appointment.starts_at < end, Appointment.ends_at > start)
    return list(db.execute(stmt).scalars().all())


def find_overlap(
    db: Session,
    provider_id: uuid.UUID,
    start: datetime,
    end: datetime,
    exclude_appointment_id: uuid.UUID | None = None,
) -> Appointment | None:
    stmt = select(Appointment).where(
        Appointment.provider_id == provider_id,
        Appointment.status.in_([s.value for s in ACTIVE_STATUSES]),
        Appointment.starts_at < end,
        Appointment.ends_at > start,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none()
