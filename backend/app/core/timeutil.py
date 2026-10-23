from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.now(UTC)


def parse_instant(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def localize(day: date, wall: time, tz: ZoneInfo) -> datetime | None:
    """Resolve provider-local wall clock to an instant.

    Returns None when the local time does not exist (spring-forward gap).
    Ambiguous times resolve to the first occurrence (fold=0).
    """
    naive = datetime.combine(day, wall)
    aware = naive.replace(tzinfo=tz, fold=0)
    instant = aware.astimezone(UTC)
    # Round-trip detection of a non-existent wall time.
    if instant.astimezone(tz).replace(tzinfo=None) != naive:
        return None
    return instant


def local_day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = localize(day, time(0, 0), tz)
    if start is None:  # pragma: no cover - midnight gaps are not observed in practice
        start = datetime.combine(day, time(0, 0), tzinfo=tz).astimezone(UTC)
    following = day + timedelta(days=1)
    end = localize(following, time(0, 0), tz)
    if end is None:  # pragma: no cover
        end = datetime.combine(following, time(0, 0), tzinfo=tz).astimezone(UTC)
    return start, end


def local_today(tz: ZoneInfo) -> date:
    return utcnow().astimezone(tz).date()


def zone(name: str) -> ZoneInfo:
    return ZoneInfo(name)
