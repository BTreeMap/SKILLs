"""Closed vocabularies and the records every boundary decodes: book files,
batch entries, and the ledger envelope."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import ConfigDict, Field, StrictFloat, StrictInt, StringConstraints

from btm_corekit import Model, Named, NonEmpty, Slug, Trimmed


class CapacityClass(StrEnum):
    UNDER_CAP = "under_cap"
    IN_BAND = "in_band"
    CROWDED = "crowded"


class Action(StrEnum):
    PROMOTE = "promote"
    REJECT = "reject"
    OVERRIDE = "override"
    PAUSE = "pause"
    RETIRE = "retire"
    APPROVE = "approve"


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Status(StrEnum):
    """A strategy's stage; the human alone writes `strategies/<name>/status`."""

    RESEARCH = "research"
    PAPER = "paper"
    LIVE = "live"
    RETIRED = "retired"


class Cadence(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class Rebalance(StrEnum):
    """When a strategy trades: the last trading day of each period."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


StrategyName = Annotated[
    str, Trimmed, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]*$")
]
"""A directory under `strategies/`: lowercase, digits, `-`, `_`; never a path."""

Quantity = Annotated[float, Field(gt=0)]
Price = Annotated[float, Field(gt=0)]
Texts = tuple[str, ...]


class OpenRow(Model):
    """Batch entries keep fields the gate does not branch on."""

    model_config = ConfigDict(frozen=True, extra="allow")


class OpenNamed(Named):
    model_config = ConfigDict(frozen=True, extra="allow")


class HypothesisEntry(OpenNamed):
    strategy: StrategyName
    family_id: NonEmpty
    capacity_class: CapacityClass
    falsifier: NonEmpty
    counterparty: NonEmpty
    min_holding_days: Annotated[int, Field(ge=1)]
    mechanism: NonEmpty | None = None
    sector: NonEmpty | None = None
    supersedes: NonEmpty | None = None


class CritiqueEntry(OpenNamed):
    run_id: NonEmpty
    blockers: Texts
    concerns: Texts
    by: NonEmpty
    supersedes: NonEmpty | None = None


class DecisionEntry(OpenNamed):
    subject: NonEmpty
    action: Action
    reason: NonEmpty
    supersedes: NonEmpty | None = None


class FillEntry(OpenRow):
    symbol: NonEmpty
    side: Side
    quantity: Quantity
    price: Price
    date: date
    strategy: StrategyName
    dry_run: bool
    supersedes: NonEmpty | None = None


class Position(OpenRow):
    symbol: NonEmpty
    quantity: Quantity
    cost_basis: Price | None = None


class HoldingsEntry(OpenRow):
    date: date
    positions: tuple[Position, ...]


class Exclusions(Model):
    symbols: Texts = ()
    sectors: Texts = ()
    countries: Texts = ()


class Preferences(Model):
    """`preferences.json`, rewritten whole by `record`; extras survive."""

    model_config = ConfigDict(frozen=True, extra="allow")

    focus_sectors: Texts
    exclusions: Exclusions
    cadence: Cadence


class Family(Model):
    """`touches` names `quality` or `low_risk` to add QMJ or BAB to the
    factor regression."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    trials: Annotated[int, Field(ge=0)]
    touches: Texts = ()


class Thresholds(Model):
    model_config = ConfigDict(frozen=True, extra="ignore")

    dsr: float
    pbo_promote: float
    pbo_discard: float
    t_empirical: float
    t_mechanism: float
    capacity_tolerance: float
    crowded_multiple: float
    drawdown_review_multiple: float
    underperform_months: int
    paper_months: int
    paper_months_long: int
    long_holding_days: int
    folds: Annotated[int, Field(ge=2)] = 5


class Sizing(Model):
    model_config = ConfigDict(frozen=True, extra="ignore")

    vol_target: float
    kelly_fraction: float
    max_weight: float


class Limits(Model):
    """`limits.json`: the human owns it, so unknown keys are ignored, not refused."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    asset_cap: Annotated[int, Field(gt=0)]
    min_holding_days: Annotated[int, Field(ge=1)]
    max_cost_share: float
    max_adv_participation: Annotated[float, Field(gt=0)]
    price_floor: float
    adv_multiple: float
    impact_coefficient: float
    commission_bps: float
    delisting: dict[str, float]
    thresholds: Thresholds
    sizing: Sizing
    repeat_tolerance: float
    families: dict[str, Family]


class StrategyConfig(Model):
    """`strategies/<name>/config.json`, agent-written, so unknown keys are
    refused; `params` are numbers only, each perturbed by 20% when scored."""

    params: dict[str, StrictInt | StrictFloat] = Field(default_factory=dict)
    rebalance: Rebalance
    holding_days: Annotated[int, Field(ge=1)]
    long_only: bool
    family_id: NonEmpty


BASELINE_CONFIG: dict[str, object] = {
    "params": {"momentum_days": 252, "skip_days": 21, "vol_days": 252},
    "rebalance": "annual",
    "holding_days": 252,
    "long_only": True,
    "family_id": "baseline",
}


BASELINE_HYPOTHESIS: dict[str, object] = {
    "kw": ["baseline", "static"],
    "strategy": "baseline",
    "family_id": "baseline",
    "capacity_class": "crowded",
    "falsifier": "net Sharpe at or below zero over the paper stage, or below "
    "the equal-weight universe net of costs",
    "counterparty": "investors who shun recent losers, volatile names, and "
    "cheap names; the premia are known and crowded",
    "min_holding_days": 252,
}


class BookMeta(Model):
    """`book.json`, the marker `start` writes and every verb demands."""

    id: Slug
    created: str
    engine: str


def limits_template(cap: int) -> dict[str, object]:
    """The spec's `limits.json` defaults, with the asset cap the caller chose."""
    return {
        "asset_cap": cap,
        "min_holding_days": 5,
        "max_cost_share": 0.25,
        "max_adv_participation": 0.02,
        "price_floor": 5,
        "adv_multiple": 50,
        "impact_coefficient": 0.1,
        "commission_bps": 1.0,
        "delisting": {"nyse": -0.30, "amex": -0.30, "nasdaq": -0.55, "merger": 0.0},
        "thresholds": {
            "dsr": 0.95,
            "pbo_promote": 0.10,
            "pbo_discard": 0.50,
            "t_empirical": 3.0,
            "t_mechanism": 2.0,
            "capacity_tolerance": 0.20,
            "crowded_multiple": 20,
            "drawdown_review_multiple": 1.5,
            "underperform_months": 12,
            "paper_months": 6,
            "paper_months_long": 12,
            "long_holding_days": 63,
            "folds": 5,
        },
        "sizing": {"vol_target": 0.10, "kelly_fraction": 0.25, "max_weight": 0.05},
        "repeat_tolerance": 1e-4,
        "families": {"baseline": {"trials": 1}},
    }


PREFERENCES_TEMPLATE: dict[str, object] = {
    "focus_sectors": [],
    "exclusions": {"symbols": [], "sectors": [], "countries": []},
    "cadence": "monthly",
}
