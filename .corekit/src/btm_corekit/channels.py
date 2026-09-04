"""The two output channels: one JSON document on stdout, advisories on stderr."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

# What survives json.dumps. Document builders return it, so a Path or a
# model is caught where it is written rather than at the print.
JSON: TypeAlias = (
    "bool | int | float | str | Sequence[JSON] | Mapping[str, JSON] | None"
)


def emit(document: Mapping[str, Any]) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)
