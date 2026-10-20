"""The continue view, pure: derived from live ledger rows on every call,
never stored."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from btm_finance.ledger import Break, Row
from btm_finance.models import Action, Limits, Status

CLOSING = frozenset({Action.REJECT, Action.RETIRE})


def by_status(names: Mapping[str, Status]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {status.value: [] for status in Status}
    for name, status in names.items():
        grouped[status.value].append(name)
    return grouped


def open_hypotheses(
    hypotheses: Sequence[Row], runs: Sequence[Row], decisions: Sequence[Row]
) -> list[Row]:
    """Registered, never scored, never rejected or retired by a decision."""
    scored = {run.get("hypothesis_id") for run in runs}
    closed = {d.get("subject") for d in decisions if d.get("action") in CLOSING}
    return [h for h in hypotheses if h.get("id") not in scored | closed]


def families(
    limits: Limits,
    hypotheses: Sequence[Row],
    runs: Sequence[Row],
    decisions: Sequence[Row],
) -> dict[str, Any]:
    """Per family: open hypotheses, trials used (every run line counts), budget."""
    used = Counter(str(run.get("family_id")) for run in runs)
    pending = open_hypotheses(hypotheses, runs, decisions)
    names = sorted(
        set(limits.families) | set(used) | {str(h.get("family_id")) for h in pending}
    )
    budget = {name: family.trials for name, family in limits.families.items()}
    return {
        name: {
            "trials_used": used[name],
            "trials": budget.get(name),
            "open": [
                {
                    "id": h.get("id"),
                    "strategy": h.get("strategy"),
                    "sector": h.get("sector"),
                    "capacity_class": h.get("capacity_class"),
                }
                for h in pending
                if h.get("family_id") == name
            ],
        }
        for name in names
    }


def open_proposals(
    dates: Sequence[str], decisions: Sequence[Row], today: date
) -> list[dict[str, Any]]:
    """A proposal file no decision names yet, with its age in days."""
    decided = {d.get("subject") for d in decisions}
    shown: list[dict[str, Any]] = []
    for stem in dates:
        if stem in decided:
            continue
        try:
            age: int | None = (today - date.fromisoformat(stem)).days
        except ValueError:
            age = None
        shown.append({"date": stem, "age_days": age})
    return shown


def next_step(
    breaks: Sequence[Break],
    hypotheses: Sequence[Row],
    pending: int,
    proposals: Sequence[Mapping[str, Any]],
) -> str:
    """The cheapest useful next action; advisory only."""
    if breaks:
        first = breaks[0]
        return (
            f"tell the operator: {first.file} line {first.line} breaks the ledger; "
            "restore from backup, never edit"
        )
    if proposals:
        return f"walk the operator through proposal {proposals[0]['date']}"
    if not hypotheses:
        return "register a hypothesis for each strategy with record, baseline first"
    if pending:
        return f"{pending} open hypotheses await strategy code and scoring"
    return "register the next hypothesis within its family budget"
