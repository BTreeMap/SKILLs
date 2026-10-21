"""Closed vocabularies and the records every boundary decodes: book files,
batch entries, and the ledger envelope."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StringConstraints,
)

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
    DIAGNOSE = "diagnose"
    FORGO = "forgo"
    """A passing sleeve left unproposed, with the reason: forgoing is a cost."""


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Status(StrEnum):
    """A strategy's stage; the human alone writes `strategies/<name>/status`."""

    RESEARCH = "research"
    PROBE = "probe"
    """Live at the fixed `sizing.probe_weight`, so out-of-sample fills accrue
    before the strategy clears the promotion thresholds."""
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


class Chain(StrEnum):
    """Chain ids of the `macro` reference's chain table; `none` cites none."""

    NONE = "none"
    TIGHTENING_INTO_LEVERAGE = "tightening-into-leverage"
    EASING_INTO_BUBBLE = "easing-into-bubble"
    DELEVERAGING_PRINTING = "deleveraging-printing"
    DELETION_UNDER_STRESS = "deletion-under-stress"
    CURRENCY_INFLATION = "currency-inflation"
    EXPECTATION_VS_OUTCOME = "expectation-vs-outcome"
    SPIN_OFF_SUPPLY = "spin-off-supply"


Quantity = Annotated[float, Field(gt=0)]
Price = Annotated[float, Field(gt=0)]
Texts = tuple[str, ...]
Confidence = Annotated[float, Field(ge=0, le=1)]


def _cited(chain: Chain) -> Chain:
    if chain is Chain.NONE:
        raise ValueError("name a chain id; none is no chain to falsify")
    return chain


Cited = Annotated[Chain, AfterValidator(_cited)]

KELLY_TOLERANCE = 0.01
"""How far `kelly_implied` may sit from `p_win - (1 - p_win) / payoff`."""


class Odds(Model):
    """The bet stated at entry: win probability, payoff (gain per unit lost,
    the b of Kelly 1956), horizon, and the Kelly fraction those imply."""

    p_win: Annotated[float, Field(gt=0, lt=1)]
    payoff: Annotated[float, Field(gt=0)]
    horizon_days: Annotated[int, Field(ge=1)]
    kelly_implied: float

    def model_post_init(self, _context: object) -> None:
        implied = self.p_win - (1.0 - self.p_win) / self.payoff
        if abs(self.kelly_implied - implied) > KELLY_TOLERANCE:
            raise ValueError(
                f"kelly_implied {self.kelly_implied} is not p_win - (1 - p_win) "
                f"/ payoff = {implied:.4f} within {KELLY_TOLERANCE}"
            )


class Attribution(Model):
    """Where a realized return came from, decimals summing to the return."""

    market: float
    factor: float
    currency: float
    idiosyncratic: float
    costs: float


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
    falsifier_by: date | None = None
    """Kill date: `check` lists the hypothesis as overdue past it."""
    odds: Odds | None = None
    """Required at promotion, not at registration."""
    mechanism: NonEmpty | None = None
    sector: NonEmpty | None = None
    supersedes: NonEmpty | None = None
    chain: Chain | None = None
    expectation_source: NonEmpty | None = None
    discounted: NonEmpty | None = None
    confidence: Confidence | None = None


class CritiqueEntry(OpenNamed):
    run_id: NonEmpty
    blockers: Texts
    concerns: Texts
    by: NonEmpty
    confidence: Confidence | None = None
    supersedes: NonEmpty | None = None


class DecisionEntry(OpenNamed):
    subject: NonEmpty
    action: Action
    reason: NonEmpty
    odds: Odds | None = None
    confidence: Confidence | None = None
    supersedes: NonEmpty | None = None


class ScoredEntry(OpenNamed):
    """A bet scored at exit: `subject` is the hypothesis id, `outcome` what
    happened in one line, scores against the odds stated at entry."""

    subject: NonEmpty
    resolved: date
    outcome: NonEmpty
    realized_return: float
    brier: Annotated[float, Field(ge=0, le=1)]
    log_score: Annotated[float, Field(le=0)]
    attribution: Attribution
    supersedes: NonEmpty | None = None


class RegimeEntry(OpenNamed):
    """A human-confirmed regime record. The gate reads `as_of`, `confidence`,
    `falsified`, `supersedes`; every other field is free JSON."""

    as_of: date
    confidence: Confidence
    falsified: tuple[Cited, ...] = ()
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
    event: bool = False


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
    tracking_error: Annotated[float, Field(gt=0)] = 0.05
    dsr_probe: float = 0.80
    pbo_probe: float = 0.25
    paper_min_days: Annotated[int, Field(ge=1)] = 63
    """Dry-run or live fill days within `tracking_error` of the model path
    before a sleeve's tier moves up."""


class KellyFractions(Model):
    """Fraction of full Kelly per evidence tier (Thorp 2006; MacLean, Thorp,
    Ziemba 2010): backtest only, paper fills, live fills."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    backtest: Annotated[float, Field(ge=0, le=1)]
    paper: Annotated[float, Field(ge=0, le=1)]
    live: Annotated[float, Field(ge=0, le=1)]


class Sizing(Model):
    model_config = ConfigDict(frozen=True, extra="ignore")

    vol_target: float
    kelly_fraction: KellyFractions
    max_weight: float
    ruin_bound: Annotated[float, Field(gt=0, lt=1)] = 0.35
    """Largest 1st-percentile 252-day loss of the whole book allowed; a breach
    scales every sleeve down (`cuts.kind: ruin`)."""
    probe_weight: Annotated[float, Field(ge=0, le=1)] = 0.02
    """Fixed weight of a `probe` sleeve."""


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
    regime_stale_days: Annotated[int, Field(ge=0)] = 90
    max_strategy_risk_share: Annotated[float, Field(gt=0, le=1)] = 0.5
    min_effective_streams: Annotated[float, Field(ge=1)] = 2.0
    model_cutoff: date | None = None
    """Training cutoff of the agent's model: folds whose test window starts
    after it are hindsight-free (`walk_forward.post_cutoff`)."""


class StrategyConfig(Model):
    """`strategies/<name>/config.json`, agent-written, so unknown keys are
    refused; `params` are numbers only, each perturbed by 20% when measured."""

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
    held_out: str | None = None
    """Absolute path of the held-out list; None reads the XDG default."""


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
            "dsr_probe": 0.80,
            "pbo_probe": 0.25,
            "paper_min_days": 63,
        },
        "sizing": {
            "vol_target": 0.20,
            "kelly_fraction": {"backtest": 0.25, "paper": 0.50, "live": 0.75},
            "max_weight": 0.10,
            "ruin_bound": 0.35,
            "probe_weight": 0.02,
        },
        "repeat_tolerance": 1e-4,
        "families": {"baseline": {"trials": 1}},
        "regime_stale_days": 90,
        "max_strategy_risk_share": 0.5,
        "min_effective_streams": 2,
        "model_cutoff": None,
    }


PREFERENCES_TEMPLATE: dict[str, object] = {
    "focus_sectors": [],
    "exclusions": {"symbols": [], "sectors": [], "countries": []},
    "cadence": "monthly",
}
