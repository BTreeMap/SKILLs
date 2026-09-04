"""The two output channels: one JSON document on stdout, advisories on stderr."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

# What survives json.dumps; a Path or a model is caught here, not at print
# time. emit stays wide since a member may hand it a TypedDict view that
# mypy cannot see as JSON-shaped.
JSON: TypeAlias = (
    "bool | int | float | str | Sequence[JSON] | Mapping[str, JSON] | None"
)


def emit(document: Mapping[str, Any]) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)
