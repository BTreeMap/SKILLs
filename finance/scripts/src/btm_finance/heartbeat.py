"""The always-on loop's pulse, pure: newest `heartbeat` pad line against
`preferences.json` `heartbeat_minutes`, quiet hours, and trials spent today.
Derived from live state on every call, never stored."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime, time
from typing import Any

from btm_finance.models import Preferences, QuietHours
from btm_finance.views import day_of

HEARTBEAT = "heartbeat"
STALE_MULTIPLE = 2
"""A pulse older than this many intervals is stale."""
START = (
    "start heartbeat: write a heartbeat pad line, schedule next wake within "
    "heartbeat_minutes"
)


def clock_of(raw: str) -> time:
    """`HH:MM`, already checked by `QuietHours`, as a time."""
    hour, minute = raw.split(":")
    return time(int(hour), int(minute))


def is_quiet(window: QuietHours | None, clock: time) -> bool:
    """`clock` inside `[start, end)`; wraps midnight when `start` is after
    `end`; empty when they are equal or no window is set."""
    if window is None:
        return False
    start, end = clock_of(window.start), clock_of(window.end)
    if start <= end:
        return start <= clock < end
    return clock >= start or clock < end


def instant(raw: object) -> datetime | None:
    """An ISO timestamp, naive read as UTC; None when it does not parse."""
    try:
        found = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    return found if found.tzinfo is not None else found.replace(tzinfo=UTC)


def last_beat(pad: Iterable[Mapping[str, Any]]) -> datetime | None:
    """Newest `ts` among `heartbeat` lines. O(pad lines)."""
    beats = (instant(row.get("ts")) for row in pad if row.get("type") == HEARTBEAT)
    return max((beat for beat in beats if beat is not None), default=None)


def pulse(
    pad: Iterable[Mapping[str, Any]],
    preferences: Preferences,
    now: datetime,
    local: time,
) -> dict[str, Any]:
    """`last` heartbeat, `minutes_since` it, `stale` past twice the interval,
    `quiet` when `local` lies in quiet hours."""
    last = last_beat(pad)
    minutes = None if last is None else int((now - last).total_seconds() // 60)
    return {
        "last": None if last is None else last.isoformat(),
        "minutes_since": minutes,
        "stale": minutes is not None
        and minutes > STALE_MULTIPLE * preferences.heartbeat_minutes,
        "quiet": is_quiet(preferences.quiet_hours, local),
    }


def stale_warning(state: Mapping[str, Any], interval: int) -> list[dict[str, Any]]:
    """One tagged warning when a heartbeat line exists and is stale."""
    if not state["stale"]:
        return []
    return [
        {
            "problem": "heartbeat stale",
            "last": state["last"],
            "minutes_since": state["minutes_since"],
            "limit": STALE_MULTIPLE * interval,
        }
    ]


def trials_today(runs: Sequence[Mapping[str, Any]], today: date) -> int:
    """Run lines of every runs file stamped `today` (UTC)."""
    return sum(1 for run in runs if day_of(run) == today)
