"""The scorecard and run line as written to `runs.jsonl`: field names fixed by
the `scorecard` reference; a number that cannot be computed is null."""

from __future__ import annotations

import math
from typing import Any

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
    is out of sample by construction."""

    folds: int
    embargo: int
    sharpe: tuple[Maybe, ...]
    mean: Maybe
    positive: Maybe


class FactorCard(Model):
    alpha_annual: Maybe
    t_alpha: Maybe
    loadings: dict[str, Maybe]
    model: str
    r2: Maybe
    n: int


class SpreadCard(Model):
    """Half-spread actually charged, trade-weighted, and both estimators on
    the traded cells with their mean absolute gap."""

    primary: str
    half_spread_mean: Maybe
    abdi_ranaldo_mean: Maybe
    corwin_schultz_mean: Maybe
    gap_mean: Maybe
    abdi_ranaldo_share: Maybe
    fallbacks: int


class Scorecard(Model):
    sharpe_gross: Maybe
    sharpe_net: Maybe
    dsr: Maybe
    trials: int
    pbo: Maybe
    walk_forward: WalkForward | None
    regimes: dict[str, dict[str, Maybe]]
    perturbation: dict[str, dict[str, Maybe]]
    factor: FactorCard | None
    turnover_annual: float
    cost_share: float
    adv_participation_max: float
    min_holding_days_realized: float
    capacity: dict[str, Maybe]
    spread_model: SpreadCard
    max_drawdown: float


class Span(Model):
    start: str
    end: str
    periods: int


class RunLine(Model):
    """One `score`: every key `score --repeat` needs to rerun it. `refused`
    lists bounds broken after running; the line counts as a trial anyway.
    `peers` are the run ids whose series fed `sr_var` and PBO, in order."""

    run_id: str
    hypothesis_id: str
    family_id: str
    strategy: str
    data_snapshot: str
    code_hash: str
    config: dict[str, Any]
    params: dict[str, float]
    scorecard: Scorecard
    reasons: dict[str, str]
    engine: dict[str, str]
    tolerance: float
    held_out: bool
    exclusions: Exclusions
    refused: tuple[str, ...]
    peers: tuple[str, ...]
    span: Span
    returns: str
    agent: str | None
