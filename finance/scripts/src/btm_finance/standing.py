"""Promotion standing, pure: derived from the live ledger on every `check
<strategy>`, never stored. Every threshold is read from `limits.json` by name."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from btm_corekit import Model
from btm_finance.ledger import Row
from btm_finance.models import Limits, Status

COMPACT = (
    "sharpe_gross",
    "sharpe_net",
    "dsr",
    "trials",
    "pbo",
    "cost_share",
    "adv_participation_max",
    "adv_clipped_share",
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
    next: str


@dataclass(frozen=True, slots=True)
class Evidence:
    """What the ledger and book hold about one strategy."""

    strategy: str
    run: Row | None
    hypothesis: Row | None
    critique: Row | None
    status: Status | None
    raw_status: str


def shown(value: float) -> str:
    return f"{value:.4g}"


def number(card: Mapping[str, Any], key: str) -> float | None:
    value = card.get(key)
    return float(value) if isinstance(value, int | float) else None


def overfit(
    card: Mapping[str, Any], reasons: Mapping[str, str], limits: Limits
) -> tuple[list[str], bool]:
    """DSR and PBO blockers against the promotion thresholds, and whether PBO
    says discard."""
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
    return blockers, discard


def residual(
    card: Mapping[str, Any], reasons: Mapping[str, str], limits: Limits, mechanism: bool
) -> list[str]:
    """The factor regression's alpha t against its threshold."""
    th = limits.thresholds
    factor = card.get("factor")
    limit = th.t_mechanism if mechanism else th.t_empirical
    if not isinstance(factor, Mapping):
        return [f"factor: null ({reasons.get('factor', 'not computed')})"]
    t = number(factor, "t_alpha")
    if t is None or t < limit:
        return [f"t_alpha: {'null' if t is None else shown(t)} vs {limit}"]
    return []


def capacity(card: Mapping[str, Any], limits: Limits) -> list[str]:
    """Net Sharpe at 1x positive and within tolerance of 0.1x."""
    curve = card.get("capacity")
    tolerance = limits.thresholds.capacity_tolerance
    levels = curve if isinstance(curve, Mapping) else {}
    small, cap = (number(levels, key) for key in ("0.1x", "1x"))
    blockers: list[str] = []
    if small is None or cap is None:
        blockers.append("capacity: null")
    elif cap <= 0.0:
        blockers.append(f"capacity: net Sharpe at 1x {shown(cap)} is not positive")
    elif abs(cap - small) > tolerance * abs(small):
        blockers.append(
            f"capacity: 1x {shown(cap)} vs 0.1x {shown(small)} beyond {tolerance}"
        )
    return blockers


def bounds(card: Mapping[str, Any], limits: Limits) -> list[str]:
    blockers: list[str] = []
    for key, limit, above in (
        ("cost_share", limits.max_cost_share, True),
        ("min_holding_days_realized", float(limits.min_holding_days), False),
    ):
        value = number(card, key)
        if value is None or (value > limit if above else value < limit):
            blockers.append(
                f"{key}: {'null' if value is None else shown(value)} vs {limit}"
            )
    return blockers


def stage(evidence: Evidence) -> list[str]:
    """Status blockers: an unknown word, or `retired`."""
    match evidence.status:
        case None:
            return [f"status: unknown {evidence.raw_status!r}"]
        case Status.RETIRED:
            return ["status: retired"]
        case Status.RESEARCH | Status.LIVE:
            return []


def next_of(standing: Standing, blockers: Sequence[str]) -> str:
    match standing:
        case Standing.DISCARD:
            return "record a reject decision; PBO says the result is overfit"
        case Standing.BLOCKED if "no critique" in blockers:
            return "delegate a critique of the run with /summon, then record it"
        case Standing.BLOCKED:
            return f"address or explain: {blockers[0]}"
        case Standing.PROMOTABLE:
            return "propose promotion to the operator; on their yes record it"


def standing_of(evidence: Evidence, limits: Limits) -> StandingView:
    """Every blocker named with value and limit; `discard` outranks
    `blocked`. A hypothesis without odds blocks promotion."""
    status = evidence.raw_status if evidence.status is None else evidence.status.value
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
            next=f"measure {evidence.strategy} after registering its hypothesis",
        )
    card = run.get("scorecard")
    card = card if isinstance(card, Mapping) else {}
    reasons = run.get("reasons")
    reasons = reasons if isinstance(reasons, Mapping) else {}
    hypothesis = evidence.hypothesis or {}
    stats, discard = overfit(card, reasons, limits)
    blockers = residual(card, reasons, limits, "mechanism" in hypothesis)
    blockers += capacity(card, limits)
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
    blockers += stage(evidence)
    if (
        not discard
        and not blockers
        and not stats
        and not isinstance(hypothesis.get("odds"), Mapping)
    ):
        named = hypothesis.get("id") or run.get("hypothesis_id")
        blockers.append(f"odds: none registered on {named}")
    blockers = stats + blockers
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
    compact["override_reason"] = run.get("override_reason")
    return StandingView(
        strategy=evidence.strategy,
        run_id=str(run.get("run_id")),
        standing=standing,
        blockers=tuple(blockers),
        scorecard=compact,
        critique=None if critique is None else str(critique.get("id")),
        status=status,
        next=next_of(standing, blockers),
    )
