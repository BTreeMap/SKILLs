"""Governed files, pure: `limits.json`, `strategies/*/status`, `approvals/*.json`
change only on the operator's word in chat; a decision's `applied` names each
one it changed and `commits` the commit holding it. Verdicts derive from git
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
Witness = tuple[str, str]  # book-relative path, commit hash


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
    """Every (path, commit) pair a decision line's `applied` and `commits`
    hold; with `action`, only that action's lines. O(lines)."""
    found: set[Witness] = set()
    for row in decisions:
        if action is not None and row.get("action") != action.value:
            continue
        applied, commits = row.get("applied"), row.get("commits")
        if isinstance(applied, list) and isinstance(commits, list):
            found |= {(str(p), str(c)) for p, c in zip(applied, commits, strict=False)}
    return found


def unnamed(
    commits: Iterable[Commit], decisions: Iterable[Row]
) -> list[dict[str, Any]]:
    """One warning per commit touching a governed file that no decision's
    `commits` holds, newest first."""
    named = {commit for _, commit in witnesses(decisions)}
    return [
        {
            "problem": UNNAMED,
            "commit": found.hash,
            "subject": found.subject,
            "files": [path for path in found.files if governed(path)],
        }
        for found in commits
        if found.hash not in named and any(governed(p) for p in found.files)
    ]


def uncommitted(dirty: Iterable[str]) -> list[dict[str, Any]]:
    """One warning per governed file that differs from HEAD or is untracked."""
    return [
        {"file": path, "problem": UNCOMMITTED}
        for path in sorted(dirty)
        if governed(path)
    ]
