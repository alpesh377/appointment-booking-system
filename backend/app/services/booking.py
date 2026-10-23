from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, conflict, forbidden
from app.core.timeutil import utcnow
from app.models import (
    ACTIVE_STATUSES,
    Appointment,
    AppointmentEvent,
    AppointmentStatus,
    ProviderProfile,
    Role,
    Service,
    User,
)
from app.repositories.appointments import (
    acquire_provider_lock,
    find_overlap,
    lock_active_appointments,
    sweep_expired,
)
from app.services.availability import get_active_service, get_provider, is_slot_available
from app.services.serialization import appointment_payload


def _hold_deadline(start: datetime, now: datetime) -> datetime:
    return min(now + timedelta(hours=settings.pending_hold_hours), start - timedelta(hours=settings.booking_notice_hours))


def _event(
    db: Session,
    appointment: Appointment,
    from_status: str | None,
    to_status: str,
    actor: User | None,
    actor_role: str,
    reason: str | None = None,
) -> None:
    db.add(
        AppointmentEvent(
            appointment_id=appointment.id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor.id if actor else None,
            actor_role=actor_role,
            reason=reason,
        )
    )


def create_booking(
    db: Session,
    customer: User,
    provider_id: uuid.UUID,
    service_id: uuid.UUID,
    starts_at: datetime,
    notes: str | None = None,
) -> dict:
    provider = get_provider(db, provider_id)
    acquire_provider_lock(db, provider.id)
    sweep_expired(db, provider.id)

    service = get_active_service(db, provider, service_id)
    now = utcnow()
    end = starts_at + timedelta(minutes=service.duration_minutes)

    if not is_slot_available(db, provider, service, starts_at, now=now):
        db.rollback()
        raise conflict("SLOT_UNAVAILABLE", "That time is no longer available.")

    lock_active_appointments(db, provider.id, starts_at, end)
    if find_overlap(db, provider.id, starts_at, end) is not None:
        db.rollback()
        raise conflict("SLOT_UNAVAILABLE", "That time is no longer available.")

    appointment = Appointment(
        id=uuid.uuid4(),
        customer_id=customer.id,
        provider_id=provider.id,
        service_id=service.id,
        starts_at=starts_at,
        ends_at=end,
        duration_minutes=service.duration_minutes,
        status=AppointmentStatus.PENDING.value,
        notes=notes,
        hold_expires_at=_hold_deadline(starts_at, now),
    )
    db.add(appointment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise conflict("SLOT_UNAVAILABLE", "That time is no longer available.") from None

    _event(
        db,
        appointment,
        None,
        AppointmentStatus.PENDING.value,
        customer,
        Role.CUSTOMER.value,
        "Appointment requested.",
    )
    db.commit()
    db.refresh(appointment)
    return appointment_payload(appointment, events=[])


def reschedule(
    db: Session,
    customer: User,
    appointment: Appointment,
    starts_at: datetime,
) -> dict:
    if appointment.customer_id != customer.id:
        raise forbidden()
    provider = appointment.provider

    acquire_provider_lock(db, provider.id)
    sweep_expired(db, provider.id)
    db.refresh(appointment)

    now = utcnow()
    if appointment.status not in {s.value for s in ACTIVE_STATUSES}:
        db.rollback()
        raise conflict("INVALID_TRANSITION", "This appointment can no longer be rescheduled.")
    if now >= appointment.starts_at - timedelta(hours=settings.booking_notice_hours):
        db.rollback()
        raise AppError(403, "CUTOFF_PASSED", "Rescheduling is no longer possible this close to the start.")

    service = appointment.service
    if not service.is_active:
        db.rollback()
        raise AppError(409, "SERVICE_INACTIVE", "The service is no longer offered.")

    if not is_slot_available(
        db,
        provider,
        service,
        starts_at,
        now=now,
        exclude_appointment_id=appointment.id,
    ):
        db.rollback()
        raise conflict("SLOT_UNAVAILABLE", "That time is no longer available.")

    end = starts_at + timedelta(minutes=appointment.duration_minutes)
    lock_active_appointments(db, provider.id, starts_at, end)
    if find_overlap(db, provider.id, starts_at, end, exclude_appointment_id=appointment.id):
        db.rollback()
        raise conflict("SLOT_UNAVAILABLE", "That time is no longer available.")

    successor_id = uuid.uuid4()
    previous_status = appointment.status
    appointment.status = AppointmentStatus.RESCHEDULED.value
    appointment.rescheduled_to_id = successor_id
    appointment.hold_expires_at = None
    db.flush()

    successor = Appointment(
        id=successor_id,
        customer_id=appointment.customer_id,
        provider_id=appointment.provider_id,
        service_id=appointment.service_id,
        starts_at=starts_at,
        ends_at=end,
        duration_minutes=appointment.duration_minutes,
        status=AppointmentStatus.PENDING.value,
        notes=appointment.notes,
        hold_expires_at=_hold_deadline(starts_at, now),
        rescheduled_from_id=appointment.id,
    )
    db.add(successor)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise conflict("SLOT_UNAVAILABLE", "That time is no longer available.") from None

    _event(
        db,
        appointment,
        previous_status,
        AppointmentStatus.RESCHEDULED.value,
        customer,
        Role.CUSTOMER.value,
        "Rescheduled.",
    )
    _event(
        db,
        successor,
        None,
        AppointmentStatus.PENDING.value,
        customer,
        Role.CUSTOMER.value,
        "Created as a reschedule of an earlier appointment.",
    )
    db.commit()
    db.refresh(successor)
    events = list(
        db.execute(
            select(AppointmentEvent)
            .where(AppointmentEvent.appointment_id == successor.id)
            .order_by(AppointmentEvent.created_at)
        ).scalars()
    )
    return appointment_payload(successor, events=events)


def provider_profile_for(db: Session, user: User) -> ProviderProfile | None:
    return user.provider_profile


def service_for_appointment(appointment: Appointment) -> Service:
    return appointment.service
