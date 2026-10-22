"""Closed vocabularies and the records every boundary decodes: book files,
batch entries, and the ledger envelope."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from pathlib import PurePosixPath
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
from btm_finance.data.tables import Source


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
    """A passing sleeve left unproposed, with the reason."""
    ONBOARD = "onboard"
    """`start` applying the operator's answers; `subject` is the book id."""


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Status(StrEnum):
    """A strategy's stage; `strategies/<name>/status` changes only on the
    operator's word, named by a decision's `applied`."""

    RESEARCH = "research"
    PROBE = "probe"
    """Live at the fixed `sizing.probe_weight`."""
    PAPER = "paper"
    LIVE = "live"
    RETIRED = "retired"


class Cadence(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class RunDays(StrEnum):
    """Which days the scheduled loop runs and the brief arrives."""

    DAILY = "daily"
    WEEKDAYS = "weekdays"


Hour = Annotated[int, Field(ge=0, le=23)]


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
    falsifier_by: date
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
    applied: tuple[NonEmpty, ...] | None = None
    """Governed files the decision changed, book-relative, each committed;
    `record` stores each one's committed blob id under `objects`."""
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


class Schedule(Model):
    """When the daily loop runs: hour (local, 0 to 23) and which days."""

    hour: Hour = 7
    days: RunDays = RunDays.WEEKDAYS


Clock = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
"""Local wall-clock time, `HH:MM`, 24-hour."""


class QuietHours(Model):
    """Local window when the heartbeat runs tiers 0 and 1 only; `start` after
    `end` wraps midnight, `start` equal to `end` is empty."""

    start: Clock
    end: Clock


HEARTBEAT_MINUTES = 45


class Preferences(Model):
    """`preferences.json`, rewritten whole by `record`; extras survive."""

    model_config = ConfigDict(frozen=True, extra="allow")

    focus_sectors: Texts
    exclusions: Exclusions
    cadence: Cadence
    schedule: Schedule | None = None
    """Absent in a book made before the daily loop."""
    heartbeat_minutes: Annotated[int, Field(ge=1)] = HEARTBEAT_MINUTES
    """Longest wait between wake-ups; `check` warns past twice it."""
    quiet_hours: QuietHours | None = None


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
    crowded_multiple: Annotated[float, Field(gt=0)] = 20.0
    crowded_cap: Annotated[int, Field(gt=0)] | None = None
    """Capital the capacity curve's top point tests; None tests
    `crowded_multiple` times `asset_cap`."""
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
    regime_stale_days: Annotated[int, Field(ge=0)] = 90
    max_strategy_risk_share: Annotated[float, Field(gt=0, le=1)] = 0.5
    min_effective_streams: Annotated[float, Field(ge=1)] = 2.0
    model_cutoff: date | None = None
    """Training cutoff of the agent's model: folds whose test window starts
    after it are hindsight-free (`walk_forward.post_cutoff`)."""
    trials_per_day: Annotated[int, Field(ge=0)] = 3
    """Run lines per UTC day `measure` writes before refusing; `--held-out`
    and `--repeat` pass."""
    idle_days: Annotated[int, Field(ge=1)] = 90
    """A `lib/` module or `tools/` script with no run or commit this many
    days lands in bare `check` `evolution.idle`."""


class StrategyConfig(Model):
    """`strategies/<name>/config.json`: unknown keys are refused; `params` are
    numbers only, each perturbed by 20% when measured."""

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
    """Skill commit at `start`, informational."""
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
            "crowded_cap": None,
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
        "trials_per_day": 3,
        "idle_days": 90,
    }


PREFERENCES_TEMPLATE: dict[str, object] = {
    "focus_sectors": [],
    "exclusions": {"symbols": [], "sectors": [], "countries": []},
    "cadence": "monthly",
    "schedule": {"hour": 7, "days": "weekdays"},
    "heartbeat_minutes": HEARTBEAT_MINUTES,
}


class AccountKind(StrEnum):
    TAXABLE = "taxable"
    SHELTERED = "sheltered"


class Account(Model):
    name: NonEmpty
    kind: AccountKind


class Broker(Model):
    """Question 2. `sleeve_account` names the account sleeves trade in; `api`
    records only whether one exists: the book never calls it."""

    name: NonEmpty | None = None
    accounts: tuple[Account, ...] = ()
    sleeve_account: NonEmpty | None = None
    api: bool = False

    def model_post_init(self, _context: object) -> None:
        names = {account.name for account in self.accounts}
        if (
            self.sleeve_account is not None
            and names
            and self.sleeve_account not in names
        ):
            raise ValueError(
                f"sleeve_account {self.sleeve_account!r} names none of accounts: "
                f"{', '.join(sorted(names))}"
            )


class Capital(Model):
    """Question 3: asset cap now (absent: `--cap`) and in six months."""

    now: Annotated[int, Field(gt=0)] | None = None
    six_months: Annotated[int, Field(gt=0)] | None = None


class Risk(Model):
    """Question 4: `sizing.ruin_bound` and `sizing.kelly_fraction.backtest`."""

    ruin_bound: Annotated[float, Field(gt=0, lt=1)] = 0.35
    kelly_backtest: Annotated[float, Field(ge=0, le=1)] = 0.25


class Horizon(Model):
    """Question 5: holding period, rebalance cadence, hour and days of the
    daily brief."""

    holding: NonEmpty = "weeks to years"
    cadence: Cadence = Cadence.MONTHLY
    brief_hour: Hour = 7
    schedule: RunDays = RunDays.WEEKDAYS


class Universe(Model):
    """Question 6. `index` names index or list; absent reads `universe.csv`."""

    index: NonEmpty | None = None
    exchanges: Texts = ()
    cap_ceiling: Annotated[float, Field(gt=0)] | None = None
    exclusions: Exclusions = Field(default_factory=Exclusions)
    focus_sectors: Texts = ()


FREE_SOURCES: tuple[Source, ...] = (Source.CSV, Source.EDGAR, Source.FRENCH)
"""Sources needing no key: the default of question 7."""


class Sources(Model):
    """Question 7: which `load` sources the book uses and EDGAR contact
    string. Never a key: keys live in the environment only."""

    used: tuple[Source, ...] = FREE_SOURCES
    edgar_contact: NonEmpty | None = None


class CollaboratorKind(StrEnum):
    AGENT = "agent"
    PERSON = "person"


class Collaborator(Model):
    name: NonEmpty
    kind: CollaboratorKind
    may_propose: bool = False


class Answers(Model):
    """`answers.json`: operator's onboarding answers; every key optional, a
    missing one takes its default; unknown keys refuse."""

    jurisdiction: NonEmpty | None = None
    currency: NonEmpty | None = None
    broker: Broker = Field(default_factory=Broker)
    capital: Capital = Field(default_factory=Capital)
    risk: Risk = Field(default_factory=Risk)
    horizon: Horizon = Field(default_factory=Horizon)
    universe: Universe = Field(default_factory=Universe)
    sources: Sources = Field(default_factory=Sources)
    model_cutoff: date | None = None
    held_out: NonEmpty | None = None
    collaborators: tuple[Collaborator, ...] = ()


ANSWERS_SHAPE: dict[str, object] = {
    "jurisdiction": "CA",
    "currency": "CAD",
    "broker": {
        "name": "<broker>",
        "accounts": [{"name": "main", "kind": "taxable"}],
        "sleeve_account": "main",
        "api": False,
    },
    "capital": {"now": 100000, "six_months": 150000},
    "risk": {"ruin_bound": 0.35, "kelly_backtest": 0.25},
    "horizon": {
        "holding": "weeks to years",
        "cadence": "monthly",
        "brief_hour": 7,
        "schedule": "weekdays",
    },
    "universe": {
        "index": "<index or list>",
        "exchanges": ["tsx", "nyse"],
        "cap_ceiling": 2000000000,
        "exclusions": {"symbols": [], "sectors": [], "countries": []},
        "focus_sectors": [],
    },
    "sources": {"used": ["csv", "edgar", "french"], "edgar_contact": "<name email>"},
    "model_cutoff": "2026-01-31",
    "held_out": "<absolute path outside the book>",
    "collaborators": [{"name": "<name>", "kind": "agent", "may_propose": False}],
}


UNIT_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
UnitName = Annotated[str, StringConstraints(pattern=UNIT_PATTERN)]
"""A delegated unit's slug: lowercase letters, digits, single inner hyphens.
Open on purpose: the spine's write-scope table names common units, and the
lead names the scope of any other unit in its brief."""


class ReceiptStatus(StrEnum):
    DONE = "done"
    PARTIAL = "partial"
    STOPPED = "stopped"


SUMMARY_WORDS = 40


def book_relative(raw: str) -> str:
    """Relative POSIX path with no `..`, drive, or backslash: under the book."""
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "\\" in raw or ":" in raw:
        raise ValueError(f"{raw!r} is outside the book; give a book-relative path")
    return raw


def _short(raw: str) -> str:
    words = len(raw.split())
    if words > SUMMARY_WORDS:
        raise ValueError(f"summary has {words} words; cut it to {SUMMARY_WORDS}")
    return raw


BookPath = Annotated[NonEmpty, AfterValidator(book_relative)]
Line = Annotated[str, Trimmed, StringConstraints(pattern=r"^[^\n\r]*$")]
"""One line of text; empty allowed."""
CommitHash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]


class Receipt(Model):
    """A delegate's whole final message. Extra keys refuse."""

    unit: UnitName
    status: ReceiptStatus
    wrote: tuple[BookPath, ...]
    pad: tuple[NonEmpty, ...]
    ids: dict[str, NonEmpty]
    summary: Annotated[NonEmpty, AfterValidator(_short)]
    next: Line
    friction: Line
    commit: CommitHash | None
    """The delegate's branch head after its last commit; None when it wrote
    nothing."""


RECEIPT_SHAPE: dict[str, object] = {
    "unit": "<slug>",
    "status": "|".join(ReceiptStatus),
    "wrote": ["<book-relative path>"],
    "pad": ["<pad id>"],
    "ids": {"run_id": "...", "hypothesis": "..."},
    "summary": f"<claim, at most {SUMMARY_WORDS} words>",
    "next": "<one line or empty>",
    "friction": "<one line or empty>",
    "commit": "<40-hex branch head, or null when nothing was written>",
}
