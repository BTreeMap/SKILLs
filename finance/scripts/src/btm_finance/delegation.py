"""Delegate briefs: `delegates/<unit>.md` files the lead writes and patches
from what receipts show. The engine reads them only to report: receipt pad
lines name the brief's git blob id as dispatched, and git holds every
version. Its only git calls are `hash-object` and `log`/`show` on one file.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import btm_finance

FOLDER = "delegates"
SEEDED = ("bet", "author", "critique")
RECEIPT = "receipt"
DONE = "done"
RECENT = 10
LESSONS = "## Lessons"


def seed(name: str) -> str:
    """The template `start` copies to `delegates/<name>.md`."""
    return (
        resources.files(btm_finance) / "templates" / FOLDER / f"{name}.md"
    ).read_text(encoding="utf-8")


def git(root: Path, *argv: str) -> str | None:
    """One git call's stdout in `root`; None when git is absent or fails."""
    found = shutil.which("git")
    if found is None:
        return None
    done = subprocess.run(
        [found, "-C", str(root), *argv], capture_output=True, check=False
    )
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else None


def blob(root: Path, relative: str) -> str | None:
    """`git hash-object` of the file as it stands; works outside a repo."""
    out = git(root, "hash-object", "--", relative)
    return out.strip() if out else None


def lessons(text: str) -> int:
    """List items under the `## Lessons` heading, up to the next heading."""
    _, found, tail = text.partition(LESSONS)
    if not found:
        return 0
    body = tail.split("\n#", 1)[0]
    return sum(1 for line in body.splitlines() if line.lstrip().startswith("- "))


def last_lesson(root: Path, relative: str) -> str | None:
    """Committer date of the newest commit that added a Lessons line, from
    `git log` of the one file; None outside a repository or before any.
    O(commits touching the file) git calls, stopping at the first hit."""
    log = git(root, "log", "--format=%H %cs", "--", relative)
    commits = [line.split() for line in (log or "").splitlines() if line.strip()]

    def count(index: int) -> int:
        if index >= len(commits):
            return 0
        return lessons(git(root, "show", f"{commits[index][0]}:{relative}") or "")

    newer = count(0)
    for index, (_, day) in enumerate(commits):
        older = count(index + 1)
        if newer > older:
            return day
        newer = older
    return None


def clean(row: Mapping[str, Any]) -> bool:
    """A receipt with status `done` and no friction."""
    return row.get("status") == DONE and not row.get("friction")


def share(rows: Sequence[Mapping[str, Any]]) -> float | None:
    return sum(map(clean, rows)) / len(rows) if rows else None


@dataclass(frozen=True, slots=True)
class Brief:
    unit: str
    path: str
    blob: str | None


def briefs(root: Path) -> list[Brief]:
    folder = root / FOLDER
    paths = sorted(folder.glob("*.md")) if folder.is_dir() else []
    return [
        Brief(p.stem, f"{FOLDER}/{p.name}", blob(root, f"{FOLDER}/{p.name}"))
        for p in paths
    ]


def table(root: Path, pad: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One row per brief: dispatches (receipt lines naming the unit, pad
    order), clean share overall and over the last ten, dispatches on the
    current blob, last lesson date. O(pad lines + git calls)."""
    receipts = [row for row in pad if row.get("type") == RECEIPT]
    rows: list[dict[str, Any]] = []
    for brief in briefs(root):
        own = [row for row in receipts if row.get("unit") == brief.unit]
        rows.append(
            {
                "unit": brief.unit,
                "dispatches": len(own),
                "clean": share(own),
                "clean_last_ten": share(own[-RECENT:]),
                "on_current": None
                if brief.blob is None
                else sum(1 for row in own if row.get("brief") == brief.blob),
                "last_lesson": last_lesson(root, brief.path),
            }
        )
    return rows
