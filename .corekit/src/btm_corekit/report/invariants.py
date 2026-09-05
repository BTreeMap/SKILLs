"""Invariant checks at a decoder boundary: a violation is a CommandError."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypeVar

from btm_corekit.report.errors import CommandError

E = TypeVar("E", bound=StrEnum)
T = TypeVar("T")


def require(condition: bool, invariant: str) -> None:
    if not condition:
        raise CommandError(invariant)


def demand(value: T | None, invariant: str) -> T:
    """The value, or the violated invariant, narrowed from optional to bound."""
    if value is None:
        raise CommandError(invariant)
    return value


def parse_enum(cls: type[E], raw: Any, what: str) -> E:
    """A raw value becomes its vocabulary member, or names the vocabulary."""
    try:
        return cls(raw)
    except ValueError as err:
        raise CommandError(f"{what} outside the vocabulary: {err}") from err
