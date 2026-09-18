"""Invariant checks at a decoder boundary: a violation is a CommandError."""

from __future__ import annotations

from typing import TypeVar

from btm_corekit.report.errors import CommandError

T = TypeVar("T")


def require(condition: bool, invariant: str) -> None:
    if not condition:
        raise CommandError(invariant)


def demand(value: T | None, invariant: str) -> T:
    """The value, or the violated invariant, narrowed from optional to bound."""
    if value is None:
        raise CommandError(invariant)
    return value
