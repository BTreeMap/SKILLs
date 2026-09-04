"""Readers for one untrusted field.

The ledger-replay boundary fails fast: a corrupt log is a defect, and the
first violation is the bug. These narrow `Any` to the domain type so a
decoder states what it wants instead of testing what it got.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from btm_corekit.errors import CommandError


def read_text(raw: Mapping[str, Any], key: str, what: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CommandError(f"{what} needs a non-empty {key}")
    return value


def read_opt_text(raw: Mapping[str, Any], key: str, what: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CommandError(f"{what} {key} must be text")
    return value


def read_texts(raw: Mapping[str, Any], key: str, what: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise CommandError(f"{what} {key} must be a list of strings")
    return tuple(value)


def read_count(raw: Mapping[str, Any], key: str, what: str, *, minimum: int = 0) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise CommandError(f"{what} needs {key} as an integer of at least {minimum}")
    return value
