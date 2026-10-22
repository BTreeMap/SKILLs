"""The daily brief, pure: at most twelve one-line strings the lead reads to
the operator verbatim, derived from live state on every call. The first line
is the cap and the book's value; the last is always one `Reply`; the book's
`lib/brief.py` lines sit between, cut to fit."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from btm_finance.views import day_of

QUESTION = "question"
ANSWER = "answer"
LINES = 12
WEEK = 7
FIXED = 4  # cap and value, breaches, counts, reply
PROPOSAL_LINES = LINES - FIXED


class Reply(StrEnum):
    """The brief's last line, first that applies in this order."""

    FILLS = "Paste your fills for {date}."
    ANSWER = "Reply approve, reject, or override {date} with a reason."
    CONFIRM = "Reply yes to apply, or say what to change."
    NOTHING = "Nothing to decide today; ask anything."


@dataclass(frozen=True, slots=True)
class Owed:
    """What the operator owes, from live state: `unfilled` the stem of an
    approved proposal no fill names; `unanswered` an open proposal's stem;
    `pending` a change the agent asked about today, unanswered."""

    unfilled: str | None = None
    unanswered: str | None = None
    pending: bool = False


def asked_today(pad: Iterable[Mapping[str, Any]], today: date) -> bool:
    """Some `question` pad line of `today` whose `ts` no `answer` line names
    in its `question` field. Pad is one-shot here: materialized once.
    O(pad lines)."""
    rows = tuple(pad)
    answered = {str(row.get(QUESTION)) for row in rows if row.get("type") == ANSWER}
    return any(
        row.get("type") == QUESTION
        and str(row.get("ts", ""))[:10] == today.isoformat()
        and str(row.get("ts")) not in answered
        for row in rows
    )


def reply(owed: Owed) -> str:
    if owed.unfilled is not None:
        return Reply.FILLS.format(date=owed.unfilled)
    if owed.unanswered is not None:
        return Reply.ANSWER.format(date=owed.unanswered)
    if owed.pending:
        return Reply.CONFIRM.format()
    return Reply.NOTHING.format()


def money(value: float) -> str:
    """Whole currency units, no separator."""
    return f"{value:.0f}"


@dataclass(frozen=True, slots=True)
class Bet:
    """One sleeve of an open proposal: tier `-` until the proposal carries it;
    `number` is the one figure that justifies the weight."""

    strategy: str
    tier: str
    weight: float | None
    odds: Mapping[str, Any] | None
    number: str


@dataclass(frozen=True, slots=True)
class Open:
    stem: str
    age_days: int | None
    bets: tuple[Bet, ...]


def figure(value: object) -> str:
    return f"{value:.3g}" if isinstance(value, int | float) else "null"


def odds_text(odds: Mapping[str, Any] | None) -> str:
    if odds is None:
        return "odds none"
    return (
        f"odds p {figure(odds.get('p_win'))} b {figure(odds.get('payoff'))} "
        f"{odds.get('horizon_days')}d"
    )


def justifying(sharpe_net: object) -> str:
    """Net Sharpe, the sizing input."""
    return f"sharpe_net {figure(sharpe_net)}"


def proposal_line(proposal: Open) -> str:
    age = "" if proposal.age_days is None else f" ({proposal.age_days}d old)"
    bets = "; ".join(
        f"{b.strategy} {b.tier} w {figure(b.weight)} {odds_text(b.odds)} {b.number}"
        for b in proposal.bets
    )
    return f"proposal {proposal.stem}{age}: {bets or 'no sleeve'}"


def proposal_lines(proposals: Sequence[Open]) -> list[str]:
    """One line each; more than fit: a count line, then the newest two."""
    if len(proposals) <= PROPOSAL_LINES:
        return [proposal_line(p) for p in proposals]
    newest = sorted(proposals, key=lambda p: p.stem)[-2:][::-1]
    head = f"{len(proposals)} open proposals; newest two below"
    return [head, *(proposal_line(p) for p in newest)]


def breaches_line(incidents: Sequence[Mapping[str, Any]], today: date) -> str:
    """Incidents in the last 7 days by strategy and kind; `integrity` lines
    name no strategy and count under `data`."""
    recent = Counter(
        (str(row.get("strategy") or "data"), str(row.get("kind")))
        for row in incidents
        if (day := day_of(row, "as_of") or day_of(row)) is not None
        and 0 <= (today - day).days < WEEK
    )
    if not recent:
        return "breaches, last 7 days: none"
    shown = ", ".join(
        f"{strategy} {kind} {n}" for (strategy, kind), n in sorted(recent.items())
    )
    return f"breaches, last 7 days: {shown}"


def brief(  # noqa: PLR0913 - one line per input, each read once
    *,
    cap: int,
    value: float,
    proposals: Sequence[Open],
    incidents: Sequence[Mapping[str, Any]],
    overdue: int,
    unscored: int,
    owed: Owed,
    next_action: str,
    today: date,
    extra: Sequence[str] = (),
) -> dict[str, Any]:
    """`next` is the agent's advisory; the operator's line is `reply`;
    `extra` the book's lines, as many as fit in twelve."""
    core = [
        f"cap {cap}, book {money(value)}",
        *proposal_lines(proposals),
        breaches_line(incidents, today),
        f"overdue {overdue}, unscored {unscored}",
    ]
    room = max(LINES - len(core) - 1, 0)
    lines = [*core, *extra[:room], reply(owed)]
    return {"lines": [" ".join(line.split()) for line in lines], "next": next_action}
