"""Closed vocabularies and the records every boundary decodes: book files,
batch entries, and the ledger envelope."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import (
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StringConstraints,
)

from btm_corekit import Model, Named, NonEmpty, Positive, Slug, Trimmed


class Action(StrEnum):
    PROMOTE = "promote"
    REJECT = "reject"
    OVERRIDE = "override"
    RETIRE = "retire"
    APPROVE = "approve"
    CLOSE = "close"
    """A bet ended: `subject` the hypothesis id, `realized` its decimal
    return, `against_odds` its result."""


class Outcome(StrEnum):
    """How a closed bet ended against the odds it was registered at."""

    WIN = "win"
    LOSS = "loss"


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Status(StrEnum):
    """A strategy's stage; `strategies/<name>/status` changes only on the
    operator's word."""

    RESEARCH = "research"
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
Confidence = Annotated[float, Field(ge=0, le=1)]


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


class OpenRow(Model):
    """Batch entries keep fields the gate does not branch on."""

    model_config = ConfigDict(frozen=True, extra="allow")


class OpenNamed(Named):
    model_config = ConfigDict(frozen=True, extra="allow")


class HypothesisEntry(OpenNamed):
    strategy: StrategyName
    family_id: NonEmpty
    falsifier: NonEmpty
    counterparty: NonEmpty
    min_holding_days: Annotated[int, Field(ge=1)]
    falsifier_by: date
    """Kill date: `check` lists the hypothesis as overdue past it."""
    odds: Odds
    """The bet stated at registration; its Kelly fraction must be above 0."""
    mechanism: NonEmpty | None = None
    sector: NonEmpty | None = None
    supersedes: NonEmpty | None = None
    confidence: Confidence | None = None

    def model_post_init(self, _context: object) -> None:
        if self.odds.kelly_implied <= 0.0:
            raise ValueError(
                f"odds.kelly_implied {self.odds.kelly_implied} is at or below 0: "
                "the stated odds hold no edge; register a bet with one, or none"
            )


class CritiqueEntry(OpenNamed):
    run_id: NonEmpty
    blockers: Texts
    concerns: Texts
    by: NonEmpty
    confidence: Confidence | None = None
    supersedes: NonEmpty | None = None


CLOSING = ("realized", "against_odds")


class DecisionEntry(OpenNamed):
    """`realized` and `against_odds` belong to `close` alone, which needs
    both."""

    subject: NonEmpty
    action: Action
    reason: NonEmpty
    odds: Odds | None = None
    confidence: Confidence | None = None
    supersedes: NonEmpty | None = None
    realized: Annotated[float, Field(allow_inf_nan=False)] | None = None
    against_odds: Outcome | None = None

    def model_post_init(self, _context: object) -> None:
        missing = [name for name in CLOSING if getattr(self, name) is None]
        if self.action is Action.CLOSE and missing:
            raise ValueError(
                f"a close decision needs {' and '.join(missing)}: realized the "
                f"bet's decimal return, against_odds {'|'.join(Outcome)}"
            )
        if self.action is not Action.CLOSE and len(missing) < len(CLOSING):
            raise ValueError("realized and against_odds belong to close alone")


class FillEntry(OpenRow):
    symbol: NonEmpty
    side: Side
    quantity: Quantity
    price: Price
    date: date
    strategy: StrategyName
    proposal: NonEmpty | None = None
    """The proposal stem the fill trades; null for `opening`."""
    supersedes: NonEmpty | None = None


class Exclusions(Model):
    symbols: Texts = ()
    sectors: Texts = ()
    countries: Texts = ()


Channel = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_]{3,31}$")]
"""A public Telegram username, Telegram's own rule; it enters a URL as is."""


class Bound(Model):
    """How far back one channel's history reaches: posts dated before `since`
    are never stored; `limit` stops backfill once that many are held."""

    since: date | None = None
    limit: Positive | None = None

    def model_post_init(self, _context: object) -> None:
        if self.since is None and self.limit is None:
            raise ValueError("give since (YYYY-MM-DD), limit (posts), or both")


class TelegramConfig(Model):
    """`requests` caps one load's pages across every channel."""

    channels: dict[Channel, Bound] = Field(default_factory=dict)
    requests: Positive = 300


class Preferences(Model):
    """`preferences.json`, edited by hand on the operator's word; extras
    survive."""

    model_config = ConfigDict(frozen=True, extra="allow")

    focus_sectors: Texts
    exclusions: Exclusions
    cadence: Cadence
    telegram: TelegramConfig | None = None


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
    drawdown_review_multiple: float
    folds: Annotated[int, Field(ge=2)] = 5
    tracking_error: Annotated[float, Field(gt=0)] = 0.05
    tracked_days: Annotated[int, Field(ge=1)] = 63
    """Calendar days real fills must span within `tracking_error` of the
    model path before a sleeve's tier moves to `tracked`."""


class KellyFractions(Model):
    """Fraction of full Kelly per evidence tier (Thorp 2006; MacLean, Thorp,
    Ziemba 2010): backtest only, or real fills tracking the model path."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    backtest: Annotated[float, Field(ge=0, le=1)]
    tracked: Annotated[float, Field(ge=0, le=1)] = 0.5


class Sizing(Model):
    model_config = ConfigDict(frozen=True, extra="ignore")

    kelly_fraction: KellyFractions
    max_weight: float
    entry_weight: Annotated[float, Field(ge=0, le=1)] = 0.02
    """Weight of a `live` sleeve with no real fills yet."""
    ruin_bound: Annotated[float, Field(gt=0, lt=1)] = 0.35
    """Largest 1st-percentile 252-day loss of the whole book allowed; a breach
    scales every sleeve down (`cuts.kind: ruin`)."""


Commission = float | dict[str, float]
"""`limits.commission_bps`: basis points for every exchange, or by exchange."""


def commission_at(commission: Commission, exchange: str) -> float | None:
    """Basis points one trade on `exchange` pays; a map's missing exchange
    reads `other`; None when the map holds neither."""
    if isinstance(commission, dict):
        return commission.get(exchange, commission.get("other"))
    return commission


def commission_ceiling(commission: Commission) -> float:
    """The largest basis points any exchange pays; 0 for an empty map."""
    if isinstance(commission, dict):
        return max(commission.values(), default=0.0)
    return commission


class Limits(Model):
    """`limits.json`: unknown keys are ignored, not refused."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    asset_cap: Annotated[int, Field(gt=0)]
    min_holding_days: Annotated[int, Field(ge=1)]
    max_cost_share: float
    max_adv_participation: Annotated[float, Field(gt=0)]
    price_floor: float
    adv_multiple: float
    impact_coefficient: float
    commission_bps: Commission
    delisting: dict[str, float]
    thresholds: Thresholds
    sizing: Sizing
    repeat_tolerance: float
    families: dict[str, Family]
    model_cutoff: date | None = None
    """Training cutoff of the agent's model: folds whose test window starts
    after it are hindsight-free (`walk_forward.post_cutoff`)."""
    trials_per_day: Annotated[int, Field(ge=0)] = 3
    """Run lines per UTC day `measure` writes before refusing; `--held-out`
    and `--repeat` pass."""
    idle_days: Annotated[int, Field(ge=1)] = 90
    """An extension no run used this many days reads idle."""


class StrategyConfig(Model):
    """`strategies/<name>/config.json`: unknown keys are refused; `params` are
    numbers only, each perturbed 20% down and up when measured;
    `holding_days` at least `limits.min_holding_days`; `family_id` the
    hypothesis's, else `measure` refuses."""

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
    "falsifier": "net Sharpe at or below zero over the paper stage, or below "
    "the equal-weight universe net of costs",
    "counterparty": "investors who shun recent losers, volatile names, and "
    "cheap names; the premia are known and crowded",
    "min_holding_days": 252,
    "odds": {"p_win": 0.55, "payoff": 1.0, "horizon_days": 252, "kelly_implied": 0.1},
}


def year_after(day: date) -> date:
    """Same day next year; 29 February lands on 28 February."""
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return day.replace(year=day.year + 1, day=28)


def baseline_hypothesis(start: date) -> dict[str, object]:
    """What `start` registers; its kill date is one year after `start`."""
    return {**BASELINE_HYPOTHESIS, "falsifier_by": year_after(start).isoformat()}


class BookMeta(Model):
    """`book.json`, the marker `start` writes and every verb demands."""

    id: Slug
    created: str
    engine: str
    """Package version at `start`, informational."""
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
            "drawdown_review_multiple": 1.5,
            "tracking_error": 0.05,
            "tracked_days": 63,
            "folds": 5,
        },
        "sizing": {
            "kelly_fraction": {"backtest": 0.25, "tracked": 0.50},
            "max_weight": 0.10,
            "entry_weight": 0.02,
            "ruin_bound": 0.35,
        },
        "repeat_tolerance": 1e-4,
        "families": {"baseline": {"trials": 1}},
        "model_cutoff": None,
        "trials_per_day": 3,
        "idle_days": 90,
    }


PREFERENCES_TEMPLATE: dict[str, object] = {
    "focus_sectors": [],
    "exclusions": {"symbols": [], "sectors": [], "countries": []},
    "cadence": "monthly",
}
