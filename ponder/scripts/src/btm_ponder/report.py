"""The two output channels: one JSON document on stdout, advisories on stderr."""

from __future__ import annotations

import json
import sys
from typing import Any


def emit(document: dict[str, Any]) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)
