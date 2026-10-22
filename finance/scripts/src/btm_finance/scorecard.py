"""The scorecard and run line as written to `runs.jsonl`: field names fixed by
the `scorecard` reference; a number that cannot be computed is null."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field

from btm_corekit import Model
from btm_finance.models import Exclusions

Maybe = float | None


def finite(value: float | None) -> Maybe:
    """JSON holds no NaN or infinity: either becomes null."""
    if value is None or not math.isfinite(value):
        return None
    return float(value)


class WalkForward(Model):
    """Net Sharpe per purged test fold; strategies fit nothing, so each fold
    is out of sample by construction. `post_cutoff`: net Sharpe of the test
    folds starting after `limits.model_cutoff`, concatenated."""

    folds: int
    embargo: int
    sharpe: tuple[Maybe, ...]
    mean: Maybe
    positive: Maybe
    post_cutoff: Maybe = None


class FactorCard(Model):
    alpha_annual: Maybe
    t_alpha: Maybe
    loadings: dict[str, Maybe]
    model: str
    r2: Maybe
    n: int


class Scorecard(Model):
    sharpe_gross: Maybe
    sharpe_net: Maybe
    dsr: Maybe
    trials: int
    pbo: Maybe
    walk_forward: WalkForward | None
    by_year: dict[str, Maybe]
    """Annualized net Sharpe per calendar year, keyed "2019"."""
    perturbation: dict[str, dict[str, Maybe]]
    factor: FactorCard | None
    turnover_annual: float
    cost_share: float
    adv_participation_max: float
    min_holding_days_realized: float
    capacity: dict[str, Maybe]
    half_spread_mean: Maybe
    """Half-spread charged, trade-weighted, decimal; `check --live` reads it."""
    max_drawdown: float
    adv_clipped: int = 0
    """(period, name) cells `measure` clipped to the ADV bound."""
    adv_clipped_share: Maybe = None
    """Gross the ADV clip removed over gross intended, whole run; null on run
    lines written before the clip."""
    extra: dict[str, Maybe] = Field(default_factory=dict)
    """One number per `lib/metrics/<name>.py`, by name; never a gate."""


class UniverseKind(StrEnum):
    """`membership`: some measured name carried `member_<index>` stretches."""

    MEMBERSHIP = "membership"
    STATIC = "static"


class Span(Model):
    start: str
    end: str
    periods: int


class RunLine(Model):
    """One `measure` run: every key `measure --repeat` needs to rerun it. `refused`
    lists bounds broken after running; the line counts as a trial anyway.
    `peers` are the run ids whose series fed `sr_var` and PBO, in order;
    `code_hash` one digest over `signal.py`, `config.json`, and each reached
    book-local module, canonical; `code_files` each of those paths to its
    own digest; `engine` the package version; `imports` what `signal.py`
    reaches from outside the book; `override_reason` the `--reason` that ran
    past a policy refusal; `asset_cap` the cap it was measured at; `trial`
    false when it re-measures its strategy's newest run, same `code_hash`,
    at a new cap, and so spends no trial; `extensions` each book hook it
    used (`<hook>/<name>`) to the digest of its AST dump; `costs` the cost
    model. Keys of older lines no field names are ignored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    run_id: str
    hypothesis_id: str
    family_id: str
    strategy: str
    data_snapshot: str
    code_hash: str | None = None
    """None on a line written before code hashes: `--repeat` refuses it."""
    code_files: dict[str, str] = Field(default_factory=dict)
    config: dict[str, Any]
    params: dict[str, float]
    scorecard: Scorecard
    reasons: dict[str, str]
    engine: str
    tolerance: float
    held_out: bool
    exclusions: Exclusions
    refused: tuple[str, ...]
    peers: tuple[str, ...]
    span: Span
    returns: str
    agent: str | None
    imports: tuple[str, ...] = ()
    universe: UniverseKind = UniverseKind.STATIC
    override_reason: str | None = None
    asset_cap: int | None = None
    """None on a line written before the stamp: read as the current cap."""
    trial: bool = True
    extensions: dict[str, str] = Field(default_factory=dict)
    costs: str = "default"
