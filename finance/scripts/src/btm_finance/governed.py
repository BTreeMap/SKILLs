"""Governed files, pure: `limits.json`, `strategies/*/status`, `approvals/*.json`
change only on the operator's word in chat; a decision's `applied` hashes
each one it changed. Verdicts derive from live hashes on every call."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from btm_finance.ledger import Row
from btm_finance.models import Action

LIMITS = "limits.json"
STATUS = "status"
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
Witness = tuple[str, str]  # book-relative path, sha256


def governed(path: str) -> bool:
    """`path`, book-relative with `/`, names a governed file."""
    match path.split("/"):
        case [only]:
            return only == LIMITS
        case ["strategies", name, last]:
            return last == STATUS and NAME.fullmatch(name) is not None
        case ["approvals", name]:
            stem, dot, ext = name.rpartition(".")
            return bool(dot and stem) and ext == "json" and not stem.startswith(".")
        case _:
            return False


def witnesses(decisions: Iterable[Row], action: Action | None = None) -> set[Witness]:
    """Every (path, sha256) a decision line's `applied` holds; with `action`,
    only that action's lines. O(lines)."""
    found: set[Witness] = set()
    for row in decisions:
        if action is not None and row.get("action") != action.value:
            continue
        applied = row.get("applied")
        for item in applied if isinstance(applied, list) else ():
            if isinstance(item, dict):
                found.add((str(item.get("path")), str(item.get("sha256"))))
    return found


def unwitnessed(
    present: Mapping[str, str], decisions: Iterable[Row]
) -> list[dict[str, Any]]:
    """One warning per governed file whose bytes no decision hashed."""
    seen = witnesses(decisions)
    return [
        {"file": path, "problem": "changed without a decision hashing it"}
        for path, digest in sorted(present.items())
        if (path, digest) not in seen
    ]
