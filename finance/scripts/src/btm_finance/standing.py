"""Promotion standing, pure: derived from the live ledger on every `check
<strategy>`, never stored. Every threshold is read from `limits.json` by name."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from btm_corekit import Model
from btm_finance.ledger import Row
from btm_finance.models import Action, CapacityClass, Limits, Status

COMPACT = (
    "sharpe_gross",
    "sharpe_net",
    "dsr",
    "trials",
    "pbo",
    "cost_share",
    "adv_participation_max",
    "min_holding_days_realized",
    "max_drawdown",
    "capacity",
)


class Standing(StrEnum):
    PROMOTABLE = "promotable"
    BLOCKED = "blocked"
    DISCARD = "discard"


class StandingView(Model):
    strategy: str
    run_id: str | None
    standing: Standing
    blockers: tuple[str, ...]
    scorecard: dict[str, Any] | None
    critique: str | None
    status: str
    paper: dict[str, Any] | None
    next: str


@dataclass(frozen=True, slots=True)
class Evidence:
    """What the ledger and book hold about one strategy today."""

    strategy: str
    run: Row | None
    hypothesis: Row | None
    critique: Row | None
    decisions: Sequence[Row]
    status: Status | None
    raw_status: str
    today: date


def shown(value: float) -> str:
    return f"{value:.4g}"


def number(card: Mapping[str, Any], key: str) -> float | None:
    value = card.get(key)
    return float(value) if isinstance(value, int | float) else None


def months_between(start: date, end: date) -> int:
    whole = (end.year - start.year) * 12 + end.month - start.month
    return whole - (end.day < start.day)


def newest(rows: Sequence[Row], subject: str, action: Action) -> Row | None:
    found = [
        row
        for row in rows
        if row.get("subject") == subject and row.get("action") == action.value
    ]
    return max(found, key=lambda row: str(row.get("ts", "")), default=None)


def statistics(
    card: Mapping[str, Any], reasons: Mapping[str, str], limits: Limits, mechanism: bool
) -> tuple[list[str], bool]:
    """DSR, PBO, and residual t blockers, and whether PBO says discard."""
    th = limits.thresholds
    blockers: list[str] = []
    dsr = number(card, "dsr")
    if dsr is None or dsr < th.dsr:
        blockers.append(f"dsr: {'null' if dsr is None else shown(dsr)} vs {th.dsr}")
    pbo = number(card, "pbo")
    discard = pbo is not None and pbo >= th.pbo_discard
    if pbo is None:
        blockers.append(f"pbo: null ({reasons.get('pbo', 'not computed')})")
    elif discard:
        blockers.append(f"pbo: {shown(pbo)} vs {th.pbo_discard} (discard)")
    elif pbo >= th.pbo_promote:
        blockers.append(f"pbo: {shown(pbo)} vs {th.pbo_promote}")
    factor = card.get("factor")
    limit = th.t_mechanism if mechanism else th.t_empirical
    if not isinstance(factor, Mapping):
        blockers.append(f"factor: null ({reasons.get('factor', 'not computed')})")
    else:
        t = number(factor, "t_alpha")
        if t is None or t < limit:
            blockers.append(f"t_alpha: {'null' if t is None else shown(t)} vs {limit}")
    return blockers, discard


def capacity(
    card: Mapping[str, Any], limits: Limits, crowded_class: bool, overridden: bool
) -> list[str]:
    """Net Sharpe at 1x positive and within tolerance of 0.1x; a crowded
    class, or 20x still within tolerance, needs an override decision."""
    curve = card.get("capacity")
    tolerance = limits.thresholds.capacity_tolerance
    levels = curve if isinstance(curve, Mapping) else {}
    small, cap, large = (number(levels, key) for key in ("0.1x", "1x", "20x"))
    blockers: list[str] = []
    if small is None or cap is None:
        blockers.append("capacity: null")
    elif cap <= 0.0:
        blockers.append(f"capacity: net Sharpe at 1x {shown(cap)} is not positive")
    elif abs(cap - small) > tolerance * abs(small):
        blockers.append(
            f"capacity: 1x {shown(cap)} vs 0.1x {shown(small)} beyond {tolerance}"
        )
    holds = (
        small is not None
        and large is not None
        and abs(large - small) <= tolerance * abs(small)
    )
    if not overridden and crowded_class:
        blockers.append("crowded: capacity_class crowded needs an override decision")
    elif not overridden and holds:
        blockers.append(
            "crowded: net Sharpe at 20x within tolerance of 0.1x needs "
            "an override decision"
        )
    return blockers


def bounds(card: Mapping[str, Any], limits: Limits) -> list[str]:
    blockers: list[str] = []
    for key, limit, above in (
        ("cost_share", limits.max_cost_share, True),
        ("adv_participation_max", limits.max_adv_participation, True),
        ("min_holding_days_realized", float(limits.min_holding_days), False),
    ):
        value = number(card, key)
        if value is None or (value > limit if above else value < limit):
            blockers.append(
                f"{key}: {'null' if value is None else shown(value)} vs {limit}"
            )
    return blockers


def stage(
    evidence: Evidence, limits: Limits, holding: int
) -> tuple[list[str], dict[str, Any] | None]:
    """Status blockers; on `paper`, months since the newest promote decision."""
    th = limits.thresholds
    match evidence.status:
        case None:
            return [f"status: unknown {evidence.raw_status!r}"], None
        case Status.RETIRED:
            return ["status: retired"], None
        case Status.RESEARCH | Status.LIVE:
            return [], None
        case Status.PAPER:
            required = (
                th.paper_months_long
                if holding > th.long_holding_days
                else th.paper_months
            )
            promoted = newest(evidence.decisions, evidence.strategy, Action.PROMOTE)
            if promoted is None:
                return ["paper_months: no promote decision names the strategy"], {
                    "required": required
                }
            since = date.fromisoformat(str(promoted.get("ts", ""))[:10])
            elapsed = months_between(since, evidence.today)
            paper = {
                "since": since.isoformat(),
                "months": elapsed,
                "required": required,
            }
            if elapsed < required:
                return [f"paper_months: {elapsed} vs {required}"], paper
            return [], paper


def next_of(standing: Standing, blockers: Sequence[str], status: Status | None) -> str:
    match standing:
        case Standing.DISCARD:
            return "record a reject decision; PBO says the result is overfit"
        case Standing.BLOCKED if "no critique" in blockers:
            return "delegate a critique of the run with /summon, then record it"
        case Standing.BLOCKED:
            return f"address or explain: {blockers[0]}"
        case Standing.PROMOTABLE if status == Status.PAPER:
            return "propose live to the operator; the human records the decision"
        case Standing.PROMOTABLE:
            return "propose promotion to the operator; the human records the decision"


def standing_of(evidence: Evidence, limits: Limits) -> StandingView:
    """Every blocker named with value and limit; `discard` outranks `blocked`."""
    status = evidence.raw_status or "none"
    run = evidence.run
    if run is None:
        return StandingView(
            strategy=evidence.strategy,
            run_id=None,
            standing=Standing.BLOCKED,
            blockers=("no run",),
            scorecard=None,
            critique=None,
            status=status,
            paper=None,
            next=f"score {evidence.strategy} after registering its hypothesis",
        )
    card = run.get("scorecard")
    card = card if isinstance(card, Mapping) else {}
    reasons = run.get("reasons")
    reasons = reasons if isinstance(reasons, Mapping) else {}
    hypothesis = evidence.hypothesis or {}
    blockers, discard = statistics(card, reasons, limits, "mechanism" in hypothesis)
    overridden = (
        newest(evidence.decisions, evidence.strategy, Action.OVERRIDE) is not None
    )
    crowded = hypothesis.get("capacity_class") == CapacityClass.CROWDED.value
    blockers += capacity(card, limits, crowded, overridden)
    blockers += bounds(card, limits)
    family = limits.families.get(str(run.get("family_id")))
    trials = number(card, "trials")
    if family is not None and trials is not None and trials > family.trials:
        blockers.append(f"trials: {int(trials)} vs budget {family.trials}")
    critique = evidence.critique
    if critique is None:
        blockers.append("no critique")
    else:
        blockers += [f"critique: {text}" for text in critique.get("blockers", [])]
    config = run.get("config")
    holding = config.get("holding_days", 0) if isinstance(config, Mapping) else 0
    found, paper = stage(evidence, limits, int(holding))
    blockers += found
    standing = (
        Standing.DISCARD
        if discard
        else Standing.BLOCKED
        if blockers
        else Standing.PROMOTABLE
    )
    compact = {key: card.get(key) for key in COMPACT}
    factor = card.get("factor")
    compact["t_alpha"] = factor.get("t_alpha") if isinstance(factor, Mapping) else None
    return StandingView(
        strategy=evidence.strategy,
        run_id=str(run.get("run_id")),
        standing=standing,
        blockers=tuple(blockers),
        scorecard=compact,
        critique=None if critique is None else str(critique.get("id")),
        status=status,
        paper=paper,
        next=next_of(standing, blockers, evidence.status),
    )
