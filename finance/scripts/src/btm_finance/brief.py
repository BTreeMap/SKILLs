"""The daily brief, pure: at most twelve one-line strings the lead reads to
the operator verbatim, derived from live state on every call."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from btm_finance.views import day_of

LINES = 12
WEEK = 7
FIXED = 4  # regime, breaches, counts, next
PROPOSAL_LINES = LINES - FIXED


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


def justifying(tier: str, sharpe_net: object, dsr: object) -> str:
    """A probe stands on DSR; every other tier on net Sharpe, the sizing input."""
    if tier == "probe":
        return f"dsr {figure(dsr)}"
    return f"sharpe_net {figure(sharpe_net)}"


def regime_line(regime: Mapping[str, Any] | None) -> str:
    if regime is None:
        return "regime: no regime"
    state = "stale" if regime.get("stale") else "fresh"
    return f"regime: {regime.get('id')} as of {regime.get('as_of')}, {state}"


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
    head = (
        f"{len(proposals)} open proposals; newest two below, check <date> for the rest"
    )
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
    regime: Mapping[str, Any] | None,
    proposals: Sequence[Open],
    incidents: Sequence[Mapping[str, Any]],
    overdue: int,
    unscored: int,
    next_action: str,
    today: date,
) -> dict[str, Any]:
    lines = [
        regime_line(regime),
        *proposal_lines(proposals),
        breaches_line(incidents, today),
        f"overdue {overdue}, unscored {unscored}",
        f"next: {next_action}",
    ]
    return {"lines": [" ".join(line.split()) for line in lines], "next": next_action}
