"""Overfitting and inference checks: PBO by CSCV, purged walk-forward folds,
OLS with Newey-West t-statistics, factor regression. Pure numpy."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from btm_finance.engine.metrics import PERIODS_PER_YEAR, Floats, Ints

TIE = 1e-9
"""Per-period block Sharpes closer than this are one value; below it,
differences are floating-point order noise, not evidence."""


@dataclass(frozen=True, slots=True, eq=False)
class Cscv:
    """PBO with its per-combination logits, block size, and rows dropped from
    the end so T divides into equal blocks."""

    pbo: float
    logits: Floats
    block_size: int
    dropped: int


def _block_sharpe(sums: Floats, squares: Floats, count: int) -> Floats:
    """Per-period Sharpe from sums and sums of squares over `count` periods."""
    mean = sums / count
    var = (squares - sums * mean) / (count - 1)
    spread = np.sqrt(np.maximum(var, 0.0))
    return np.divide(mean, spread, out=np.zeros_like(mean), where=spread > 0.0)


def cscv(returns_matrix: Floats, *, blocks: int = 16) -> Cscv:
    """Probability of backtest overfitting (Bailey, Borwein, Lopez de Prado, Zhu
    2017) on T by N per-period trial returns; O(T N + C B N), C = comb(B, B/2).

    The T mod B trailing rows are dropped; a zero-spread block set gives Sharpe 0.
    """
    matrix = np.asarray(returns_matrix, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] < 2:  # noqa: PLR2004 - T by N, N >= 2
        raise ValueError("pbo needs a T by N matrix with N at least 2 trials")
    if blocks < 2 or blocks % 2:  # noqa: PLR2004 - two halves at least
        raise ValueError("pbo needs an even number of blocks, at least 2")
    periods, trials = matrix.shape
    if periods < 2 * blocks:
        raise ValueError(f"pbo needs T at least 2 * blocks = {2 * blocks} periods")
    if np.isnan(matrix).any():
        raise ValueError("pbo needs NaN-free returns")
    size = periods // blocks
    used = matrix[: size * blocks].reshape(blocks, size, trials)
    sums, squares = used.sum(axis=1), (used**2).sum(axis=1)
    chosen = np.array(list(combinations(range(blocks), blocks // 2)), dtype=np.int64)
    member = np.zeros((chosen.shape[0], blocks), dtype=np.float64)
    np.put_along_axis(member, chosen, 1.0, axis=1)
    in_sums, in_squares = member @ sums, member @ squares
    half = size * blocks // 2
    in_sr = _block_sharpe(in_sums, in_squares, half)
    out_sr = _block_sharpe(sums.sum(0) - in_sums, squares.sum(0) - in_squares, half)
    # Ties within TIE: trials whose series coincide on a block set tie exactly
    # in arithmetic, and BLAS summation order would otherwise break the tie
    # differently per machine and move PBO by a few counts. The first trial
    # within TIE of the maximum wins; only trials worse by more than TIE rank
    # below it.
    best = np.argmax(in_sr >= in_sr.max(axis=1, keepdims=True) - TIE, axis=1)
    best_out = np.take_along_axis(out_sr, best[:, None], axis=1)
    rank = 1 + (out_sr < best_out - TIE).sum(axis=1)
    relative = rank / (trials + 1)
    logits = np.log(relative / (1.0 - relative))
    return Cscv(float(np.mean(logits < 0.0)), logits, size, periods - size * blocks)


def pbo(returns_matrix: Floats, *, blocks: int = 16) -> float:
    """PBO alone, a probability in [0, 1]; see `cscv` for logits and cost."""
    return cscv(returns_matrix, blocks=blocks).pbo


def purged_folds(n: int, *, folds: int, embargo: int) -> tuple[tuple[Ints, Ints], ...]:
    """(train, test) index pairs over n periods: contiguous test blocks, training
    is the rest minus `embargo` periods on each side of the test block; O(folds n)."""
    if folds < 2 or folds > n:  # noqa: PLR2004 - one fold leaves no training set
        raise ValueError("purged_folds needs 2 <= folds <= n")
    if embargo < 0:
        raise ValueError("purged_folds needs embargo >= 0")
    index = np.arange(n, dtype=np.int64)
    pairs = []
    for test in np.array_split(index, folds):
        start, stop = int(test[0]), int(test[-1]) + 1
        keep = (index < start - embargo) | (index >= stop + embargo)
        pairs.append((index[keep], test))
    return tuple(pairs)


@dataclass(frozen=True, slots=True)
class Ols:
    """OLS with intercept: per-period alpha, slopes, Newey-West t-statistics,
    centred R^2, Bartlett lag count, observation count."""

    alpha: float
    t_alpha: float
    betas: tuple[float, ...]
    t_betas: tuple[float, ...]
    r2: float
    lags: int
    n: int


def default_lags(n: int) -> int:
    """Newey-West (1994) rule floor(4 (T / 100)^(2/9)); O(1)."""
    return math.floor(4.0 * float((n / 100.0) ** (2.0 / 9.0)))


def ols_hac(y: Floats, X: Floats, *, lags: int | None = None) -> Ols:
    """OLS of y on [1, X] with Newey-West HAC errors, Bartlett kernel, no small-
    sample correction; lags 0 is White HC0; NaN-free; O(T k^2 L), k columns, L lags."""
    target = np.asarray(y, dtype=np.float64).reshape(-1)
    regressors = np.asarray(X, dtype=np.float64)
    if regressors.ndim == 1:
        regressors = regressors[:, None]
    n = target.size
    if regressors.shape[0] != n:
        raise ValueError("y and X must have the same number of rows")
    if np.isnan(target).any() or np.isnan(regressors).any():
        raise ValueError("ols_hac needs NaN-free y and X")
    design = np.column_stack((np.ones(n), regressors))
    k = design.shape[1]
    if n <= k:
        raise ValueError(f"ols_hac needs more than {k} observations")
    lag_count = default_lags(n) if lags is None else lags
    if lag_count < 0:
        raise ValueError("lags must be >= 0")
    coef, *_ = np.linalg.lstsq(design, target, rcond=None)
    residual = target - design @ coef
    moments = design * residual[:, None]
    meat = moments.T @ moments
    for lag in range(1, min(lag_count, n - 1) + 1):
        cross = moments[lag:].T @ moments[:-lag]
        meat += (1.0 - lag / (lag_count + 1.0)) * (cross + cross.T)
    bread = np.linalg.pinv(design.T @ design)
    errors = np.sqrt(np.maximum(np.diag(bread @ meat @ bread), 0.0))
    t = np.divide(coef, errors, out=np.full(k, np.nan), where=errors > 0.0)
    total = float(np.sum((target - target.mean()) ** 2))
    r2 = 1.0 - float(residual @ residual) / total if total > 0.0 else math.nan
    return Ols(
        alpha=float(coef[0]),
        t_alpha=float(t[0]),
        betas=tuple(coef[1:].tolist()),
        t_betas=tuple(t[1:].tolist()),
        r2=r2,
        lags=lag_count,
        n=n,
    )


@dataclass(frozen=True, slots=True)
class FactorFit:
    """Annualized alpha (decimal), its Newey-West t, loadings by factor name,
    model label such as ff5+mom, R^2, observation count."""

    alpha_annual: float
    t_alpha: float
    loadings: dict[str, float]
    model: str
    r2: float
    n: int


_CORE = (
    ("ff5", ("mktrf", "smb", "hml", "rmw", "cma")),
    ("ff3", ("mktrf", "smb", "hml")),
)
_ALIASES = {"umd": "mom", "wml": "mom"}


def model_label(factor_names: tuple[str, ...]) -> str:
    """Label from factor names, case and punctuation ignored: ff5 or ff3 core,
    then each other factor, sorted, joined by +; O(k log k)."""
    keys = [re.sub(r"[^a-z0-9]", "", name.lower()) for name in factor_names]
    keys = [_ALIASES.get(key, key) for key in keys]
    for label, core in _CORE:
        if set(core) <= set(keys):
            rest = sorted(key for key in keys if key not in core)
            return "+".join((label, *rest))
    return "+".join(sorted(keys))


def factor_regression(
    strategy_excess: Floats,
    factors_matrix: Floats,
    factor_names: tuple[str, ...],
    periods_per_year: int = PERIODS_PER_YEAR,
) -> FactorFit:
    """Per-period strategy excess on T by k factor returns via `ols_hac`; alpha
    annualized as alpha * P, decimal; O(T k^2 L)."""
    fit = ols_hac(strategy_excess, factors_matrix)
    if len(factor_names) != len(fit.betas):
        raise ValueError("factor_names must name every factor column")
    return FactorFit(
        alpha_annual=fit.alpha * periods_per_year,
        t_alpha=fit.t_alpha,
        loadings=dict(zip(factor_names, fit.betas, strict=True)),
        model=model_label(factor_names),
        r2=fit.r2,
        n=fit.n,
    )
