from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, conflict, forbidden, not_found
from app.core.timeutil import local_day_bounds, utcnow, zone
from app.models import (
    ACTIVE_STATUSES,
    Appointment,
    AppointmentEvent,
    AppointmentStatus,
    ProviderProfile,
    Role,
    User,
)
from app.repositories.appointments import acquire_provider_lock, sweep_expired
from app.services.availability import is_slot_available
from app.services.serialization import appointment_payload, event_payload


def _role_of(user: User) -> str:
    return user.role


def _provider_owner(user: User, appointment: Appointment) -> bool:
    profile = user.provider_profile
    return profile is not None and appointment.provider_id == profile.id


def get_visible(db: Session, user: User, appointment_id: uuid.UUID) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise not_found("Appointment")
    if user.role == Role.ADMIN.value:
        return appointment
    if user.role == Role.CUSTOMER.value and appointment.customer_id == user.id:
        return appointment
    if user.role == Role.PROVIDER.value and _provider_owner(user, appointment):
        return appointment
    raise forbidden()


def _events(db: Session, appointment_id: uuid.UUID) -> list[AppointmentEvent]:
    return list(
        db.execute(
            select(AppointmentEvent)
            .where(AppointmentEvent.appointment_id == appointment_id)
            .order_by(AppointmentEvent.created_at, AppointmentEvent.id)
        ).scalars()
    )


def detail(db: Session, user: User, appointment_id: uuid.UUID) -> dict:
    appointment = get_visible(db, user, appointment_id)
    return appointment_payload(appointment, events=_events(db, appointment.id))


def _append_event(
    db: Session,
    appointment: Appointment,
    from_status: str,
    to_status: str,
    user: User | None,
    actor_role: str,
    reason: str | None = None,
) -> None:
    db.add(
        AppointmentEvent(
            appointment_id=appointment.id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=user.id if user else None,
            actor_role=actor_role,
            reason=reason,
        )
    )


def _guarded(db: Session, user: User, appointment_id: uuid.UUID) -> Appointment:
    appointment = get_visible(db, user, appointment_id)
    acquire_provider_lock(db, appointment.provider_id)
    sweep_expired(db, appointment.provider_id)
    db.refresh(appointment)
    return appointment


def confirm(db: Session, user: User, appointment_id: uuid.UUID) -> dict:
    appointment = _guarded(db, user, appointment_id)
    if not _provider_owner(user, appointment):
        db.rollback()
        raise forbidden()
    if appointment.status != AppointmentStatus.PENDING.value:
        db.rollback()
        raise conflict("INVALID_TRANSITION", "Only a pending request can be confirmed.")
    appointment.status = AppointmentStatus.CONFIRMED.value
    appointment.hold_expires_at = None
    _append_event(
        db,
        appointment,
        AppointmentStatus.PENDING.value,
        AppointmentStatus.CONFIRMED.value,
        user,
        Role.PROVIDER.value,
    )
    db.commit()
    db.refresh(appointment)
    return appointment_payload(appointment, events=_events(db, appointment.id))


def reject(db: Session, user: User, appointment_id: uuid.UUID, reason: str | None = None) -> dict:
    appointment = _guarded(db, user, appointment_id)
    if not _provider_owner(user, appointment):
        db.rollback()
        raise forbidden()
    if appointment.status != AppointmentStatus.PENDING.value:
        db.rollback()
        raise conflict("INVALID_TRANSITION", "Only a pending request can be rejected.")
    appointment.status = AppointmentStatus.REJECTED.value
    appointment.hold_expires_at = None
    _append_event(
        db,
        appointment,
        AppointmentStatus.PENDING.value,
        AppointmentStatus.REJECTED.value,
        user,
        Role.PROVIDER.value,
        reason,
    )
    db.commit()
    db.refresh(appointment)
    return appointment_payload(appointment, events=_events(db, appointment.id))


def cancel(
    db: Session, user: User, appointment_id: uuid.UUID, reason: str | None = None
) -> dict:
    appointment = _guarded(db, user, appointment_id)
    now = utcnow()
    status = appointment.status

    if status not in {s.value for s in ACTIVE_STATUSES}:
        db.rollback()
        raise conflict("INVALID_TRANSITION", "This appointment can no longer be cancelled.")

    if user.role == Role.CUSTOMER.value:
        if appointment.customer_id != user.id:
            db.rollback()
            raise forbidden()
        if now >= appointment.starts_at - timedelta(hours=settings.booking_notice_hours):
            db.rollback()
            raise AppError(403, "CUTOFF_PASSED", "This appointment can no longer be cancelled.")
        actor_role = "customer"
    elif user.role == Role.PROVIDER.value:
        if not _provider_owner(user, appointment):
            db.rollback()
            raise forbidden()
        if status == AppointmentStatus.PENDING.value:
            db.rollback()
            raise conflict("USE_REJECT", "Pending requests must be rejected, not cancelled.")
        if now >= appointment.ends_at:
            db.rollback()
            raise conflict("INVALID_TRANSITION", "This appointment has already ended.")
        actor_role = "provider"
    else:
        actor_role = "admin"

    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.hold_expires_at = None
    appointment.cancelled_by_role = actor_role
    appointment.cancelled_by_user_id = user.id
    appointment.cancellation_reason = reason
    _append_event(
        db,
        appointment,
        status,
        AppointmentStatus.CANCELLED.value,
        user,
        actor_role.upper() if actor_role != "admin" else Role.ADMIN.value,
        reason,
    )
    db.commit()
    db.refresh(appointment)
    return appointment_payload(appointment, events=_events(db, appointment.id))


def complete(db: Session, user: User, appointment_id: uuid.UUID) -> dict:
    appointment = _guarded(db, user, appointment_id)
    if not _provider_owner(user, appointment):
        db.rollback()
        raise forbidden()
    if appointment.status != AppointmentStatus.CONFIRMED.value:
        db.rollback()
        raise conflict("INVALID_TRANSITION", "Only a confirmed appointment can be completed.")
    if utcnow() < appointment.ends_at:
        db.rollback()
        raise conflict("INVALID_TRANSITION", "This appointment has not ended yet.")
    appointment.status = AppointmentStatus.COMPLETED.value
    _append_event(
        db,
        appointment,
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.COMPLETED.value,
        user,
        Role.PROVIDER.value,
    )
    db.commit()
    db.refresh(appointment)
    return appointment_payload(appointment, events=_events(db, appointment.id))


def list_appointments(
    db: Session,
    user: User,
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    view: str | None = None,
    provider_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
) -> list[dict]:
    now = utcnow()
    stmt = select(Appointment)
    if user.role == Role.CUSTOMER.value:
        stmt = stmt.where(Appointment.customer_id == user.id)
    elif user.role == Role.PROVIDER.value:
        profile = user.provider_profile
        if profile is None:
            return []
        stmt = stmt.where(Appointment.provider_id == profile.id)
    else:
        if provider_id is not None:
            stmt = stmt.where(Appointment.provider_id == provider_id)
        if customer_id is not None:
            stmt = stmt.where(Appointment.customer_id == customer_id)

    if status:
        stmt = stmt.where(Appointment.status == status)
    if date_from is not None:
        stmt = stmt.where(
            Appointment.starts_at >= datetime.combine(date_from, time.min).replace(tzinfo=now.tzinfo)
        )
    if date_to is not None:
        exclusive = datetime.combine(date_to + timedelta(days=1), time.min).replace(tzinfo=now.tzinfo)
        stmt = stmt.where(Appointment.starts_at < exclusive)

    if view == "upcoming":
        stmt = stmt.where(Appointment.ends_at >= now).order_by(Appointment.starts_at.asc())
    elif view == "past":
        stmt = stmt.where(Appointment.ends_at < now).order_by(Appointment.starts_at.desc())
    elif view == "cancelled":
        stmt = stmt.where(Appointment.status == AppointmentStatus.CANCELLED.value).order_by(
            Appointment.starts_at.desc()
        )
    else:
        stmt = stmt.order_by(Appointment.starts_at.desc())

    return [appointment_payload(a) for a in db.execute(stmt).scalars()]


def customer_dashboard(db: Session, user: User) -> dict:
    stmt = select(Appointment).where(Appointment.customer_id == user.id)
    rows = list(db.execute(stmt.order_by(Appointment.starts_at.asc())).scalars())
    now = utcnow()
    active = {s.value for s in ACTIVE_STATUSES}
    upcoming = [a for a in rows if a.status in active and a.ends_at >= now]
    past = [
        a
        for a in rows
        if a.status != AppointmentStatus.CANCELLED.value
        and not (a.status in active and a.ends_at >= now)
    ]
    cancelled = [a for a in rows if a.status == AppointmentStatus.CANCELLED.value]
    return {
        "upcoming": [appointment_payload(a) for a in upcoming],
        "past": [appointment_payload(a) for a in reversed(past)],
        "cancelled": [appointment_payload(a) for a in reversed(cancelled)],
    }


def provider_conflicts(db: Session, profile: ProviderProfile) -> list[Appointment]:
    now = utcnow()
    rows = list(
        db.execute(
            select(Appointment).where(
                Appointment.provider_id == profile.id,
                Appointment.status.in_([s.value for s in ACTIVE_STATUSES]),
                Appointment.starts_at > now + timedelta(hours=settings.booking_notice_hours),
            )
        ).scalars()
    )
    return [
        a
        for a in rows
        if not is_slot_available(
            db,
            profile,
            a.service,
            a.starts_at,
            now=now,
            exclude_appointment_id=a.id,
        )
    ]


def provider_dashboard(db: Session, user: User) -> dict:
    profile: ProviderProfile | None = user.provider_profile
    if profile is None:
        raise forbidden()

    acquire_provider_lock(db, profile.id)
    sweep_expired(db, profile.id)
    db.commit()

    tz = zone(profile.timezone)
    now = utcnow()
    today_start, today_end = local_day_bounds(now.astimezone(tz).date(), tz)

    rows = list(
        db.execute(
            select(Appointment)
            .where(Appointment.provider_id == profile.id)
            .order_by(Appointment.starts_at.asc())
        ).scalars()
    )

    today = [
        a
        for a in rows
        if today_start <= a.starts_at < today_end
        and a.status
        in {
            AppointmentStatus.PENDING.value,
            AppointmentStatus.CONFIRMED.value,
            AppointmentStatus.COMPLETED.value,
        }
    ]
    pending = [a for a in rows if a.status == AppointmentStatus.PENDING.value]
    upcoming = [
        a
        for a in rows
        if a.starts_at >= now
        and a.status in {AppointmentStatus.PENDING.value, AppointmentStatus.CONFIRMED.value}
        and a not in today
    ]
    awaiting = [
        a
        for a in rows
        if a.status == AppointmentStatus.CONFIRMED.value and a.ends_at < now
    ]
    conflicts = provider_conflicts(db, profile)

    return {
        "today": [appointment_payload(a) for a in today],
        "upcoming": [appointment_payload(a) for a in upcoming],
        "pending": [appointment_payload(a) for a in pending],
        "awaiting_completion": [appointment_payload(a) for a in awaiting],
        "conflicts": [appointment_payload(a) for a in conflicts],
    }
