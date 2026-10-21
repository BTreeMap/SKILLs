"""Ruin of a weighted book, pure: stationary block bootstrap (Politis and
Romano 1994) of the joint daily returns, loss at a low wealth quantile."""

from __future__ import annotations

import numpy as np

from btm_finance.engine.metrics import PERIODS_PER_YEAR, Floats

PATHS = 1000
BLOCK = 21  # mean block length, trading days
QUANTILE = 0.01


def ruin_loss(  # noqa: PLR0913 - the bootstrap's knobs, named
    returns: Floats,
    weights: Floats,
    *,
    seed: int,
    paths: int = PATHS,
    horizon: int = PERIODS_PER_YEAR,
    block: float = BLOCK,
    quantile: float = QUANTILE,
) -> float:
    """1 minus the `quantile` of compounded wealth over `horizon` days.

    `returns` is T by S on common dates, `weights` S; each path draws whole
    rows, so cross-sleeve correlation survives. Blocks start at a uniform
    row, run circularly, end with probability 1 / `block` each day. Seeded
    generator: same inputs, same loss. O(T S + P H) time, O(P H) space.
    """
    book = np.asarray(returns, dtype=np.float64) @ np.asarray(weights, np.float64)
    rows = len(book)
    if rows == 0:
        raise ValueError("ruin_loss needs at least one row")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, rows, size=(paths, horizon))
    fresh = rng.random((paths, horizon)) < 1.0 / block
    fresh[:, 0] = True
    step = np.arange(horizon)
    opened = np.maximum.accumulate(np.where(fresh, step, 0), axis=1)
    origin = np.take_along_axis(starts, opened, axis=1)
    index = (origin + step - opened) % rows
    wealth = np.prod(1.0 + book[index], axis=1)
    return float(1.0 - np.quantile(wealth, quantile))
