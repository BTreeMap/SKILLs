"""Governed files, pure: `limits.json`, `strategies/*/status`, `approvals/*.json`
change only on the operator's word in chat; a decision's `applied` names each
one it changed and `objects` its committed blob id. Verdicts derive from git
and the ledger on every call."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from btm_finance.git import Commit
from btm_finance.ledger import Row
from btm_finance.models import Action

LIMITS = "limits.json"
STATUS = "status"
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
PATHSPECS = (LIMITS, "strategies/*/status", "approvals/*.json")
UNNAMED = "commit no decision names"
UNCOMMITTED = "governed file not committed"
Witness = tuple[str, str]  # book-relative path, blob id


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
    """Every (path, blob id) pair a decision line's `objects` holds; with
    `action`, only that action's lines. O(lines)."""
    found: set[Witness] = set()
    for row in decisions:
        if action is not None and row.get("action") != action.value:
            continue
        objects = row.get("objects")
        if isinstance(objects, dict):
            found |= {(str(path), str(blob)) for path, blob in objects.items()}
    return found


def unnamed(
    commits: Iterable[Commit], decisions: Iterable[Row]
) -> list[dict[str, Any]]:
    """One warning per commit leaving a governed file at a blob no decision's
    `objects` names, newest first."""
    named = witnesses(decisions)
    found: list[dict[str, Any]] = []
    for commit in commits:
        files = [
            path
            for path, blob in commit.blobs
            if governed(path) and blob is not None and (path, blob) not in named
        ]
        if files:
            found.append(
                {
                    "problem": UNNAMED,
                    "commit": commit.hash,
                    "subject": commit.subject,
                    "files": files,
                }
            )
    return found


def uncommitted(dirty: Iterable[str]) -> list[dict[str, Any]]:
    """One warning per governed file that differs from HEAD or is untracked."""
    return [
        {"file": path, "problem": UNCOMMITTED}
        for path in sorted(dirty)
        if governed(path)
    ]
