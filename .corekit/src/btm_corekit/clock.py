"""UTC timestamps at second precision, the one stamp format state files use."""

from __future__ import annotations

from datetime import UTC, datetime


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
