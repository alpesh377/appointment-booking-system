from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, not_found
from app.core.timeutil import local_day_bounds, utcnow, zone
from app.models import (
    ACTIVE_STATUSES,
    Appointment,
    AvailabilityRule,
    DateOverride,
    DateOverrideWindow,
    ProviderProfile,
    ScheduleBreak,
    Service,
)
from app.services.slot_engine import Override, generate_slots


def get_provider(db: Session, provider_id: uuid.UUID, require_active: bool = True) -> ProviderProfile:
    provider = db.get(ProviderProfile, provider_id)
    if provider is None or (require_active and not provider.is_active):
        raise not_found("Provider")
    return provider


def get_service(db: Session, provider: ProviderProfile, service_id: uuid.UUID) -> Service:
    service = db.get(Service, service_id)
    if service is None or service.provider_id != provider.id:
        raise not_found("Service")
    return service


def get_active_service(db: Session, provider: ProviderProfile, service_id: uuid.UUID) -> Service:
    service = get_service(db, provider, service_id)
    if not service.is_active:
        raise AppError(409, "SERVICE_INACTIVE", "This service is no longer offered.")
    return service


def load_slots(
    db: Session,
    provider: ProviderProfile,
    service: Service,
    date_from: date,
    date_to: date,
    now: datetime | None = None,
    exclude_appointment_id: uuid.UUID | None = None,
) -> list[datetime]:
    tz = zone(provider.timezone)
    now = now or utcnow()

    rules = db.execute(
        select(AvailabilityRule).where(AvailabilityRule.provider_id == provider.id)
    ).scalars()
    weekly_windows: dict[int, list[tuple]] = defaultdict(list)
    for rule in rules:
        weekly_windows[rule.weekday].append((rule.start_time, rule.end_time))

    breaks = db.execute(
        select(ScheduleBreak).where(ScheduleBreak.provider_id == provider.id)
    ).scalars()
    weekly_breaks: list[tuple[int, object, object]] = []
    date_breaks: list[tuple[date, object, object]] = []
    for item in breaks:
        if item.weekday is not None:
            weekly_breaks.append((item.weekday, item.start_time, item.end_time))
        elif item.on_date is not None:
            date_breaks.append((item.on_date, item.start_time, item.end_time))

    override_rows = list(
        db.execute(select(DateOverride).where(DateOverride.provider_id == provider.id)).scalars()
    )
    override_windows: dict[uuid.UUID, list[tuple]] = defaultdict(list)
    if override_rows:
        rows = db.execute(
            select(DateOverrideWindow).where(
                DateOverrideWindow.override_id.in_([o.id for o in override_rows])
            )
        ).scalars()
        for window in rows:
            override_windows[window.override_id].append((window.start_time, window.end_time))

    overrides = {
        row.date: Override(
            is_closed=row.is_closed,
            windows=tuple(override_windows.get(row.id, [])),
        )
        for row in override_rows
    }

    range_start, _ = local_day_bounds(date_from, tz)
    _, range_end = local_day_bounds(date_to, tz)
    busy_stmt = select(Appointment).where(
        Appointment.provider_id == provider.id,
        Appointment.status.in_([s.value for s in ACTIVE_STATUSES]),
        Appointment.ends_at > range_start,
        Appointment.starts_at < range_end,
    )
    if exclude_appointment_id is not None:
        busy_stmt = busy_stmt.where(Appointment.id != exclude_appointment_id)
    busy = [(a.starts_at, a.ends_at) for a in db.execute(busy_stmt).scalars()]

    return generate_slots(
        tz=tz,
        duration_minutes=service.duration_minutes,
        date_from=date_from,
        date_to=date_to,
        weekly_windows=weekly_windows,
        weekly_breaks=weekly_breaks,
        date_breaks=date_breaks,
        overrides=overrides,
        busy=busy,
        now=now,
        horizon_days=settings.scheduling_horizon_days,
        notice_hours=settings.booking_notice_hours,
    )


def is_slot_available(
    db: Session,
    provider: ProviderProfile,
    service: Service,
    start: datetime,
    now: datetime | None = None,
    exclude_appointment_id: uuid.UUID | None = None,
) -> bool:
    now = now or utcnow()
    local_day = start.astimezone(zone(provider.timezone)).date()
    slots = load_slots(
        db,
        provider,
        service,
        local_day,
        local_day,
        now=now,
        exclude_appointment_id=exclude_appointment_id,
    )
    return start == next((slot for slot in slots if slot == start), None)


def slot_bounds(provider: ProviderProfile, service: Service, start: datetime) -> tuple[datetime, datetime]:
    return start, start + timedelta(minutes=service.duration_minutes)
