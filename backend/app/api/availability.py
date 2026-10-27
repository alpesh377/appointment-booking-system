from __future__ import annotations

import uuid
from datetime import date, time

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import require_provider
from app.core.errors import AppError, forbidden, not_found
from app.core.timeutil import utcnow, zone
from app.db import get_db
from app.models import (
    AvailabilityRule,
    DateOverride,
    DateOverrideWindow,
    ProviderProfile,
    ScheduleBreak,
    User,
)
from app.repositories.appointments import acquire_provider_lock, sweep_expired
from app.schemas import BreaksUpdate, OverridesUpdate, WindowsUpdate
from app.services import lifecycle
from app.services.availability import get_active_service, get_provider, load_slots
from app.services.serialization import appointment_payload

router = APIRouter(tags=["availability"])


def _owned_provider(user: User, provider_id: uuid.UUID) -> ProviderProfile:
    if user.provider_profile is None or user.provider_profile.id != provider_id:
        raise forbidden()
    return user.provider_profile


def _validate_windows(windows: list[tuple[int, time, time]]) -> None:
    by_day: dict[int, list[tuple[time, time]]] = {}
    for weekday, start, end in windows:
        by_day.setdefault(weekday, []).append((start, end))
    for weekday, items in by_day.items():
        items.sort()
        for index in range(len(items) - 1):
            if items[index][1] > items[index + 1][0]:
                raise AppError(
                    422,
                    "VALIDATION_ERROR",
                    "Working windows overlap.",
                    {"windows": f"Windows overlap on weekday {weekday}."},
                )


def _validate_override_windows(windows: list[tuple[time, time]]) -> None:
    ordered = sorted(windows)
    for index in range(len(ordered) - 1):
        if ordered[index][1] > ordered[index + 1][0]:
            raise AppError(
                422,
                "VALIDATION_ERROR",
                "Override windows overlap.",
                {"windows": "Override windows must not overlap."},
            )


def _availability_state(db: Session, provider: ProviderProfile) -> dict:
    rules = list(
        db.execute(
            select(AvailabilityRule)
            .where(AvailabilityRule.provider_id == provider.id)
            .order_by(AvailabilityRule.weekday, AvailabilityRule.start_time)
        ).scalars()
    )
    breaks = list(
        db.execute(
            select(ScheduleBreak)
            .where(ScheduleBreak.provider_id == provider.id)
            .order_by(ScheduleBreak.weekday, ScheduleBreak.on_date, ScheduleBreak.start_time)
        ).scalars()
    )
    overrides = list(
        db.execute(
            select(DateOverride).where(DateOverride.provider_id == provider.id).order_by(DateOverride.date)
        ).scalars()
    )
    windows_by_override: dict[uuid.UUID, list[dict]] = {}
    if overrides:
        rows = db.execute(
            select(DateOverrideWindow).where(DateOverrideWindow.override_id.in_([o.id for o in overrides]))
        ).scalars()
        for window in rows:
            windows_by_override.setdefault(window.override_id, []).append(
                {"start_time": window.start_time.isoformat(), "end_time": window.end_time.isoformat()}
            )

    return {
        "provider_id": str(provider.id),
        "timezone": provider.timezone,
        "windows": [
            {
                "id": str(rule.id),
                "weekday": rule.weekday,
                "start_time": rule.start_time.isoformat(),
                "end_time": rule.end_time.isoformat(),
            }
            for rule in rules
        ],
        "breaks": [
            {
                "id": str(item.id),
                "weekday": item.weekday,
                "date": item.on_date.isoformat() if item.on_date else None,
                "start_time": item.start_time.isoformat(),
                "end_time": item.end_time.isoformat(),
            }
            for item in breaks
        ],
        "overrides": [
            {
                "id": str(item.id),
                "date": item.date.isoformat(),
                "is_closed": item.is_closed,
                "note": item.note,
                "windows": sorted(windows_by_override.get(item.id, []), key=lambda w: w["start_time"]),
            }
            for item in overrides
        ],
    }


@router.get("/availability", summary="Available start times")
def availability(
    provider_id: uuid.UUID,
    service_id: uuid.UUID,
    date_from: date,
    date_to: date,
    db: Session = Depends(get_db),
) -> dict:
    if date_to < date_from:
        raise AppError(422, "VALIDATION_ERROR", "The date range is invalid.")
    provider = get_provider(db, provider_id)
    service = get_active_service(db, provider, service_id)
    acquire_provider_lock(db, provider.id)
    sweep_expired(db, provider.id)
    db.commit()
    slots = load_slots(db, provider, service, date_from, date_to)
    return {
        "provider_id": str(provider.id),
        "service_id": str(service.id),
        "timezone": provider.timezone,
        "slots": [slot.isoformat() for slot in slots],
    }


@router.get("/providers/{provider_id}/availability", summary="Own availability configuration")
def read_availability(
    provider_id: uuid.UUID,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    provider = _owned_provider(user, provider_id)
    return _availability_state(db, provider)


@router.put("/providers/{provider_id}/availability/windows", summary="Replace working windows")
def replace_windows(
    provider_id: uuid.UUID,
    payload: WindowsUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    provider = _owned_provider(user, provider_id)
    windows = [(item.weekday, item.start_time, item.end_time) for item in payload.windows]
    _validate_windows(windows)
    db.execute(delete(AvailabilityRule).where(AvailabilityRule.provider_id == provider.id))
    for weekday, start, end in windows:
        db.add(AvailabilityRule(provider_id=provider.id, weekday=weekday, start_time=start, end_time=end))
    db.commit()
    return _availability_state(db, provider)


@router.put("/providers/{provider_id}/availability/breaks", summary="Replace breaks")
def replace_breaks(
    provider_id: uuid.UUID,
    payload: BreaksUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    provider = _owned_provider(user, provider_id)
    today = utcnow().astimezone(zone(provider.timezone)).date()
    scheduled: list[ScheduleBreak] = []
    for item in payload.breaks:
        if item.date is not None and item.date < today:
            raise AppError(422, "VALIDATION_ERROR", "Availability cannot be edited for past dates.")
        scheduled.append(
            ScheduleBreak(
                provider_id=provider.id,
                weekday=item.weekday,
                on_date=item.date,
                start_time=item.start_time,
                end_time=item.end_time,
            )
        )
    db.execute(delete(ScheduleBreak).where(ScheduleBreak.provider_id == provider.id))
    for item in scheduled:
        db.add(item)
    db.commit()
    return _availability_state(db, provider)


@router.put("/providers/{provider_id}/availability/overrides", summary="Upsert date overrides")
def upsert_overrides(
    provider_id: uuid.UUID,
    payload: OverridesUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    provider = _owned_provider(user, provider_id)
    today = utcnow().astimezone(zone(provider.timezone)).date()
    seen: set[date] = set()
    parsed: list[tuple[date, bool, str | None, list[tuple[time, time]]]] = []
    for item in payload.overrides:
        if item.date in seen:
            raise AppError(422, "VALIDATION_ERROR", "A date may have only one override.")
        seen.add(item.date)
        if item.date < today:
            raise AppError(422, "VALIDATION_ERROR", "Availability cannot be edited for past dates.")
        windows: list[tuple[time, time]] = []
        if not item.is_closed:
            windows = [(window.start_time, window.end_time) for window in item.windows]
            _validate_override_windows(windows)
        parsed.append((item.date, item.is_closed, item.note, windows))

    for on_date, is_closed, note, windows in parsed:
        existing = db.execute(
            select(DateOverride).where(DateOverride.provider_id == provider.id, DateOverride.date == on_date)
        ).scalar_one_or_none()
        if existing is None:
            existing = DateOverride(provider_id=provider.id, date=on_date)
            db.add(existing)
            db.flush()
        existing.is_closed = is_closed
        existing.note = note
        db.execute(delete(DateOverrideWindow).where(DateOverrideWindow.override_id == existing.id))
        for start, end in windows:
            db.add(DateOverrideWindow(override_id=existing.id, start_time=start, end_time=end))
    db.commit()
    return _availability_state(db, provider)


@router.delete("/providers/{provider_id}/availability/overrides/{on_date}", summary="Remove a date override")
def delete_override(
    provider_id: uuid.UUID,
    on_date: date,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    provider = _owned_provider(user, provider_id)
    override = db.execute(
        select(DateOverride).where(DateOverride.provider_id == provider.id, DateOverride.date == on_date)
    ).scalar_one_or_none()
    if override is None:
        raise not_found("Date override")
    db.delete(override)
    db.commit()
    return _availability_state(db, provider)


@router.get(
    "/providers/{provider_id}/availability/conflicts",
    summary="Appointments outside current availability",
)
def conflicts(
    provider_id: uuid.UUID,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> list[dict]:
    provider = _owned_provider(user, provider_id)
    return [appointment_payload(a) for a in lifecycle.provider_conflicts(db, provider)]
