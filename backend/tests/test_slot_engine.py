from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.slot_engine import Override, generate_slots

TZ = ZoneInfo("UTC")


def slots_for(
    *,
    day: date,
    duration: int,
    windows: list[tuple[time, time]],
    now: datetime | None = None,
    weekly_breaks=None,
    date_breaks=None,
    overrides=None,
    busy=None,
) -> list[datetime]:
    return generate_slots(
        tz=TZ,
        duration_minutes=duration,
        date_from=day,
        date_to=day,
        weekly_windows={day.weekday(): windows},
        weekly_breaks=weekly_breaks or [],
        date_breaks=date_breaks or [],
        overrides=overrides or {},
        busy=busy or [],
        now=now or datetime.combine(day - timedelta(days=1), time(0, 0), tzinfo=UTC),
    )


def test_slots_tile_from_window_start():
    day = date(2026, 6, 1)
    slots = slots_for(day=day, duration=30, windows=[(time(9), time(12))])
    assert [s.strftime("%H:%M") for s in slots] == [
        "09:00",
        "09:30",
        "10:00",
        "10:30",
        "11:00",
        "11:30",
    ]


def test_slot_may_not_straddle_a_break():
    day = date(2026, 6, 1)
    slots = slots_for(
        day=day,
        duration=30,
        windows=[(time(9), time(12))],
        weekly_breaks=[(day.weekday(), time(9, 45), time(10, 15))],
    )
    assert [s.strftime("%H:%M") for s in slots] == ["09:00", "10:30", "11:00", "11:30"]


def test_unused_tail_is_not_offered():
    day = date(2026, 6, 1)
    slots = slots_for(day=day, duration=30, windows=[(time(9), time(10, 20))])
    assert [s.strftime("%H:%M") for s in slots] == ["09:00", "09:30"]


def test_busy_appointment_removes_overlapping_candidates():
    day = date(2026, 6, 1)
    busy = [
        (
            datetime.combine(day, time(10), tzinfo=UTC),
            datetime.combine(day, time(10, 45), tzinfo=UTC),
        )
    ]
    slots = slots_for(day=day, duration=30, windows=[(time(9), time(12))], busy=busy)
    assert [s.strftime("%H:%M") for s in slots] == ["09:00", "09:30", "11:00", "11:30"]


def test_horizon_bounds_availability():
    day = date(2026, 6, 1)
    now = datetime.combine(day - timedelta(days=31), time(0, 0), tzinfo=UTC)
    slots = slots_for(day=day, duration=30, windows=[(time(9), time(12))], now=now)
    assert slots == []


def test_notice_boundary_is_exclusive():
    day = date(2026, 6, 1)
    now = datetime.combine(day, time(7, 0), tzinfo=UTC)
    slots = slots_for(day=day, duration=30, windows=[(time(9), time(10))], now=now)
    assert [s.strftime("%H:%M") for s in slots] == ["09:30"]
    now = datetime.combine(day, time(6, 59), tzinfo=UTC)
    slots = slots_for(day=day, duration=30, windows=[(time(9), time(10))], now=now)
    assert [s.strftime("%H:%M") for s in slots] == ["09:00", "09:30"]


def test_closed_override_removes_the_day():
    day = date(2026, 6, 1)
    slots = slots_for(
        day=day,
        duration=30,
        windows=[(time(9), time(12))],
        overrides={day: Override(is_closed=True)},
    )
    assert slots == []


def test_open_override_replaces_weekly_windows():
    day = date(2026, 6, 1)
    slots = slots_for(
        day=day,
        duration=60,
        windows=[(time(9), time(17))],
        overrides={day: Override(is_closed=False, windows=((time(10), time(14)),))},
    )
    assert [s.strftime("%H:%M") for s in slots] == ["10:00", "11:00", "12:00", "13:00"]


def test_date_break_affects_one_date_only():
    day = date(2026, 6, 1)
    other = date(2026, 6, 2)
    slots = generate_slots(
        tz=TZ,
        duration_minutes=60,
        date_from=day,
        date_to=other,
        weekly_windows={0: [(time(9), time(12))], 1: [(time(9), time(12))]},
        weekly_breaks=[],
        date_breaks=[(day, time(10), time(11))],
        overrides={},
        busy=[],
        now=datetime.combine(day - timedelta(days=1), time(0, 0), tzinfo=UTC),
    )
    assert [s.strftime("%m-%d %H:%M") for s in slots] == [
        "06-01 09:00",
        "06-01 11:00",
        "06-02 09:00",
        "06-02 10:00",
        "06-02 11:00",
    ]


def test_spring_forward_nonexistent_time_is_skipped():
    tz = ZoneInfo("America/New_York")
    day = date(2026, 3, 8)
    slots = generate_slots(
        tz=tz,
        duration_minutes=60,
        date_from=day,
        date_to=day,
        weekly_windows={day.weekday(): [(time(1), time(4))]},
        weekly_breaks=[],
        date_breaks=[],
        overrides={},
        busy=[],
        now=datetime.combine(date(2026, 3, 1), time(0, 0), tzinfo=UTC),
    )
    assert [s.astimezone(tz).strftime("%H:%M") for s in slots] == ["01:00", "03:00"]


def test_fall_back_uses_first_occurrence():
    tz = ZoneInfo("America/New_York")
    day = date(2026, 11, 1)
    slots = generate_slots(
        tz=tz,
        duration_minutes=60,
        date_from=day,
        date_to=day,
        weekly_windows={day.weekday(): [(time(0), time(3))]},
        weekly_breaks=[],
        date_breaks=[],
        overrides={},
        busy=[],
        now=datetime.combine(date(2026, 10, 25), time(0, 0), tzinfo=UTC),
    )
    first_one_am = [s for s in slots if s.astimezone(tz).hour == 1][0]
    assert first_one_am.astimezone(UTC).hour == 5


def test_local_day_boundaries_follow_dst():
    from app.core.timeutil import local_day_bounds

    tz = ZoneInfo("America/New_York")
    start, end = local_day_bounds(date(2026, 3, 8), tz)
    assert end - start == timedelta(hours=23)
