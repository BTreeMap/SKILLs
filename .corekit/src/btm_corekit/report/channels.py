"""The two output channels: one JSON document on stdout, advisories on stderr.

The document is indented when stdout is a terminal, for a person reading
it, and one line when stdout is a pipe or a file, for the agent parsing it:
the line form drops the indentation, about a third of a batch report's
bytes, and loses nothing. Both forms keep json's default `": "` separator,
so a `grep '"ok": true'` matches either.
"""

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
    indent = 2 if sys.stdout.isatty() else None
    print(json.dumps(document, indent=indent, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)
