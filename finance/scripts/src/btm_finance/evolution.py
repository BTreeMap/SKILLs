"""Bare `check` `evolution`, pure: brief use, `lib/` use, `tools/` age, and
the idle list, derived from receipts, run lines, and commit dates on every
call; never written."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from btm_finance.ledger import Row

RECEIPT = "receipt"
ISO_DATE = len("YYYY-MM-DD")


def day(stamp: object) -> str | None:
    """The ISO date leading a timestamp; None for anything else."""
    if isinstance(stamp, str) and len(stamp) >= ISO_DATE:
        return stamp[:ISO_DATE]
    return None


def latest(*stamps: str | None) -> str | None:
    return max((s for s in stamps if s), default=None)


def briefs_of(slugs: Iterable[str], pad: Sequence[Row]) -> dict[str, dict[str, Any]]:
    """Per brief: receipt lines naming its unit, those with a `friction`,
    newest receipt `ts`. O(pad lines)."""
    found: dict[str, dict[str, Any]] = {
        slug: {"dispatches": 0, "frictions": 0, "last": None} for slug in sorted(slugs)
    }
    for row in pad:
        entry = found.get(str(row.get("unit"))) if row.get("type") == RECEIPT else None
        if entry is None:
            continue
        entry["dispatches"] += 1
        entry["frictions"] += bool(str(row.get("friction") or "").strip())
        entry["last"] = latest(entry["last"], str(row.get("ts") or "") or None)
    return found


def evolution(  # noqa: PLR0913 - every input is one derived fact
    *,
    briefs: Iterable[str],
    pad: Sequence[Row],
    runs: Sequence[Row],
    lib: Iterable[str],
    tools: Iterable[str],
    commits: Mapping[str, str],
    today: date,
    idle_days: int,
) -> dict[str, Any]:
    """`commits` maps a path to its last commit date. `idle`: each committed
    `lib/` module or `tools/` script whose newest run or commit is over
    `idle_days` before `today`. O(pad + runs * paths + files)."""
    uses: Counter[str] = Counter()
    last_run: dict[str, str] = {}
    for run in runs:
        paths = run.get("code_paths")
        for path in paths if isinstance(paths, list) else []:
            uses[str(path)] += 1
            last_run[str(path)] = (
                latest(last_run.get(str(path)), day(run.get("ts"))) or ""
            )
    modules, tools = sorted(lib), sorted(tools)
    committed = {path: day(commits.get(path)) for path in [*modules, *tools]}
    cutoff = (today - timedelta(days=idle_days)).isoformat()
    idle = [
        path
        for path, stamp in committed.items()
        if stamp is not None and (latest(stamp, last_run.get(path)) or "") < cutoff
    ]
    return {
        "briefs": briefs_of(briefs, pad),
        "lib": {
            path: {
                "runs": uses[path],
                "last_run": last_run.get(path) or None,
                "last_commit": committed[path],
            }
            for path in modules
        },
        "tools": {path: {"last_commit": committed[path]} for path in tools},
        "idle": sorted(idle),
    }
