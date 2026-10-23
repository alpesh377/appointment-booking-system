from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.timeutil import localize, utcnow


@dataclass(frozen=True)
class Override:
    is_closed: bool
    windows: tuple[tuple[time, time], ...] = ()


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def generate_slots(
    *,
    tz: ZoneInfo,
    duration_minutes: int,
    date_from: date,
    date_to: date,
    weekly_windows: dict[int, list[tuple[time, time]]],
    weekly_breaks: list[tuple[int, time, time]],
    date_breaks: list[tuple[date, time, time]],
    overrides: dict[date, Override],
    busy: list[tuple[datetime, datetime]],
    now: datetime | None = None,
    horizon_days: int = 30,
    notice_hours: int = 2,
) -> list[datetime]:
    """Pure slot generation.

    Candidates are anchored at each effective window start and step by the
    service duration. A candidate is emitted only when the whole interval fits
    inside the window and intersects neither a break nor an active appointment.
    """
    if duration_minutes <= 0:
        return []

    now = now or utcnow()
    notice_cutoff = now + timedelta(hours=notice_hours)
    today = now.astimezone(tz).date()
    horizon_end = today + timedelta(days=horizon_days)

    breaks_by_weekday: dict[int, list[tuple[time, time]]] = {}
    for weekday, start, end in weekly_breaks:
        breaks_by_weekday.setdefault(weekday, []).append((start, end))
    breaks_by_date: dict[date, list[tuple[time, time]]] = {}
    for on_date, start, end in date_breaks:
        breaks_by_date.setdefault(on_date, []).append((start, end))

    slots: list[datetime] = []
    day = max(date_from, today)
    last = min(date_to, horizon_end)

    while day <= last:
        override = overrides.get(day)
        if override is not None and override.is_closed:
            day += timedelta(days=1)
            continue

        if override is not None:
            windows = list(override.windows)
        else:
            windows = weekly_windows.get(day.weekday(), [])

        raw_breaks = breaks_by_weekday.get(day.weekday(), []) + breaks_by_date.get(day, [])
        break_intervals: list[tuple[datetime, datetime]] = []
        for break_start, break_end in raw_breaks:
            bs = localize(day, break_start, tz)
            be = localize(day, break_end, tz)
            if bs is not None and be is not None:
                break_intervals.append((bs, be))

        for window_start, window_end in windows:
            anchor = datetime.combine(day, window_start)
            limit = datetime.combine(day, window_end)
            step = timedelta(minutes=duration_minutes)
            candidate = anchor
            while candidate + step <= limit:
                candidate_end = candidate + step
                start_instant = localize(day, candidate.time(), tz)
                end_instant = (
                    start_instant + timedelta(minutes=duration_minutes)
                    if start_instant is not None
                    else None
                )
                if start_instant is not None and end_instant is not None:
                    blocked = any(
                        _overlaps(start_instant, end_instant, bs, be) for bs, be in break_intervals
                    )
                    if not blocked:
                        blocked = any(
                            _overlaps(start_instant, end_instant, bs, be) for bs, be in busy
                        )
                    if not blocked and start_instant > notice_cutoff:
                        slots.append(start_instant)
                candidate = candidate_end

        day += timedelta(days=1)

    slots.sort()
    return slots
