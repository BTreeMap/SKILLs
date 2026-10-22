"""The continue view, pure: derived from live ledger rows on every call,
never stored."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from btm_finance.ledger import Row
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
    """Registered, never measured, never rejected or retired by a decision."""
    measured = {run.get("hypothesis_id") for run in runs}
    closed = {d.get("subject") for d in decisions if d.get("action") in CLOSING}
    return [h for h in hypotheses if h.get("id") not in measured | closed]


def extensions(every_line: Sequence[Row]) -> list[Row]:
    """Hypothesis lines whose `falsifier_by` is later than that of the line
    they supersede; a target carrying none compares equal: more time spends
    a trial."""
    kill = {h.get("id"): day_of(h, "falsifier_by") for h in every_line}
    found: list[Row] = []
    for h in every_line:
        if "supersedes" not in h:
            continue
        before, after = kill.get(h["supersedes"]), day_of(h, "falsifier_by")
        if after is not None and before is not None and after > before:
            found.append(h)
    return found


def families(
    limits: Limits,
    hypotheses: Sequence[Row],
    runs: Sequence[Row],
    decisions: Sequence[Row],
    every_line: Sequence[Row],
) -> dict[str, Any]:
    """Per family: open hypotheses, trials used (every run line, and every
    hypothesis line extending the kill date of the line it supersedes), budget."""
    used = Counter(str(run.get("family_id")) for run in runs)
    used.update(str(h.get("family_id")) for h in extensions(every_line))
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


def day_of(row: Mapping[str, Any], key: str = "ts") -> date | None:
    """A row's ISO date under `key`, its first ten characters; None if none."""
    try:
        return date.fromisoformat(str(row.get(key, ""))[:10])
    except ValueError:
        return None


def bets_closed(decisions: Sequence[Row]) -> set[Any]:
    """Subjects of `close` decisions: hypothesis ids whose bet ended."""
    return {d.get("subject") for d in decisions if d.get("action") == Action.CLOSE}


def overdue(
    hypotheses: Sequence[Row],
    decisions: Sequence[Row],
    retired: frozenset[str],
    today: date,
) -> list[dict[str, Any]]:
    """Live hypotheses past `falsifier_by`, strategy not retired, no reject or
    retire naming strategy or id, no close decision naming the id."""
    closed = {d.get("subject") for d in decisions if d.get("action") in CLOSING}
    done = bets_closed(decisions)
    found: list[dict[str, Any]] = []
    for h in hypotheses:
        due = day_of(h, "falsifier_by")
        strategy = h.get("strategy")
        if (
            due is None
            or due >= today
            or strategy in retired
            or {strategy, h.get("id")} & closed
            or h.get("id") in done
        ):
            continue
        found.append(
            {
                "problem": "overdue",
                "hypothesis": h.get("id"),
                "strategy": strategy,
                "falsifier_by": due.isoformat(),
                "days_overdue": (today - due).days,
            }
        )
    return found


def unscored(
    hypotheses: Sequence[Row], decisions: Sequence[Row], today: date
) -> list[dict[str, Any]]:
    """Live hypotheses with `odds` whose strategy's newest promote decision is
    over `odds.horizon_days` calendar days old, no close decision naming the
    id."""
    done = bets_closed(decisions)
    promoted: dict[Any, date] = {}
    for d in decisions:
        day = day_of(d)
        if d.get("action") == Action.PROMOTE.value and day is not None:
            promoted[d.get("subject")] = max(day, promoted.get(d.get("subject"), day))
    found: list[dict[str, Any]] = []
    for h in hypotheses:
        odds, since = h.get("odds"), promoted.get(h.get("strategy"))
        horizon = odds.get("horizon_days") if isinstance(odds, Mapping) else None
        if since is None or not isinstance(horizon, int) or h.get("id") in done:
            continue
        due = since + timedelta(days=horizon)
        if today > due:
            found.append(
                {
                    "problem": "unscored",
                    "hypothesis": h.get("id"),
                    "strategy": h.get("strategy"),
                    "due": due.isoformat(),
                }
            )
    return found


def has_trials(family: Mapping[str, Any]) -> bool:
    """A budgeted family with a trial left."""
    budget = family.get("trials")
    return budget is not None and family["trials_used"] < budget


def next_step(
    hypotheses: Sequence[Row],
    pending: int,
    proposals: Sequence[Mapping[str, Any]],
    late: Sequence[Mapping[str, Any]] = (),
    budgets: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """The cheapest useful next action; advisory only. `late` holds overdue
    and unscored warnings; `budgets` the `families` view, None when unknown."""
    if proposals:
        return f"walk the operator through proposal {proposals[0]['date']}"
    if late:
        first = late[0]
        if first["problem"] == "overdue":
            return (
                f"hypothesis {first['hypothesis']} passed falsifier_by "
                f"{first['falsifier_by']}: record close, reject, or a "
                "superseding hypothesis"
            )
        return f"close hypothesis {first['hypothesis']}: record a close decision"
    if not hypotheses:
        return "register a hypothesis for each strategy with record, baseline first"
    if pending:
        return f"{pending} open hypotheses await strategy code and measure"
    return budget_step(budgets)


def budget_step(budgets: Mapping[str, Mapping[str, Any]] | None) -> str:
    """Register within budget, or, every family spent, ask for more."""
    if budgets is None or any(map(has_trials, budgets.values())):
        return "register the next hypothesis within its family budget"
    spent = ", ".join(
        f"{name} trials_used {family['trials_used']} of {family['trials']}"
        for name, family in budgets.items()
    )
    return (
        "every family is at budget: write a question pad entry asking the "
        f"operator for more trials, naming {spent}"
    )


def trials_today(runs: Sequence[Mapping[str, Any]], today: date) -> int:
    """Run lines of every runs file stamped `today` (UTC)."""
    return sum(1 for run in runs if day_of(run) == today)
