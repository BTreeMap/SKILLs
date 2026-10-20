"""Return-series metrics: Sharpe, its moments, deflated Sharpe, drawdown,
turnover, cost share, regime split. Pure numpy; returns are decimal, not %."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
from numpy.typing import NDArray

Floats = NDArray[np.float64]
Ints = NDArray[np.int64]

PERIODS_PER_YEAR = 252
# Euler-Mascheroni constant, the weight in the expected maximum of N normals.
EULER_GAMMA = 0.5772156649015329
_NORMAL = NormalDist()


def _series(returns: Floats, what: str = "returns") -> Floats:
    """One-dimensional float64 view; NaN anywhere is a caller error."""
    series = np.asarray(returns, dtype=np.float64).reshape(-1)
    if np.isnan(series).any():
        raise ValueError(f"{what} must be NaN-free")
    return series


def sharpe(returns: Floats, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """Annualized Sharpe of per-period excess returns: mean / std(ddof=1) * sqrt(P).
    NaN-free input required; O(T). Zero spread gives +-inf by sign of mean, nan at 0.

    Fewer than two periods give nan.
    """
    series = _series(returns)
    if series.size < 2:  # noqa: PLR2004 - ddof=1 needs two observations
        return math.nan
    mean = float(series.mean())
    if np.ptp(series) == 0.0:
        return math.copysign(math.inf, mean) if mean != 0.0 else math.nan
    return mean / float(series.std(ddof=1)) * math.sqrt(periods_per_year)


def annualized_return(
    returns: Floats, periods_per_year: int = PERIODS_PER_YEAR
) -> float:
    """Compound annual growth of per-period simple returns, decimal; O(T).
    NaN-free input required; empty input gives nan."""
    series = _series(returns)
    if series.size == 0:
        return math.nan
    wealth = float(np.prod(1.0 + series))
    if wealth <= 0.0:
        return -1.0
    return float(wealth ** (periods_per_year / series.size)) - 1.0


def annualized_vol(returns: Floats, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """Annualized volatility: per-period std(ddof=1) * sqrt(P), decimal; O(T).
    NaN-free input required; fewer than two periods give nan."""
    series = _series(returns)
    if series.size < 2:  # noqa: PLR2004 - ddof=1 needs two observations
        return math.nan
    return float(series.std(ddof=1)) * math.sqrt(periods_per_year)


def max_drawdown(returns: Floats) -> float:
    """Largest peak-to-trough loss of wealth cumprod(1 + r) from a start of 1,
    as a positive decimal (0.25 is a 25% fall); NaN-free input; O(T)."""
    series = _series(returns)
    wealth = np.concatenate(([1.0], np.cumprod(1.0 + series)))
    peak = np.maximum.accumulate(wealth)
    return float(np.max(1.0 - wealth / peak))


def turnover_annual(weights: Floats, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """Mean one-way turnover per period, 0.5 * sum |w_t - w_t-1|, times P.
    Weights T by N, decimal of capital; NaN means zero weight; O(T N)."""
    held = np.nan_to_num(np.asarray(weights, dtype=np.float64), nan=0.0)
    if held.ndim == 1:
        held = held[:, None]
    if held.shape[0] < 2:  # noqa: PLR2004 - a change needs two rows
        return 0.0
    one_way = 0.5 * np.abs(np.diff(held, axis=0)).sum(axis=1)
    return float(one_way.mean()) * periods_per_year


def cost_share(gross: Floats, net: Floats) -> float:
    """Share of gross PnL lost to costs: 1 - sum(net) / sum(gross), clipped to
    [0, 1]; per-period returns, NaN-free; O(T).

    Non-positive gross PnL gives 1.0 when costs are positive, else 0.0.
    """
    gross_pnl = float(_series(gross, "gross").sum())
    costs = gross_pnl - float(_series(net, "net").sum())
    if gross_pnl <= 0.0:
        return 1.0 if costs > 0.0 else 0.0
    return min(max(costs / gross_pnl, 0.0), 1.0)


def sr_moments(returns: Floats) -> tuple[float, float, float]:
    """Per-period (sr, skew, raw kurtosis) of a NaN-free series; kurtosis is 3
    for a normal. sr uses std(ddof=1), skew and kurtosis population moments; O(T)."""
    series = _series(returns)
    if series.size < 2:  # noqa: PLR2004 - ddof=1 needs two observations
        return math.nan, math.nan, math.nan
    centred = series - series.mean()
    m2 = float(np.mean(centred**2))
    if m2 == 0.0:
        return math.nan, math.nan, math.nan
    sr = float(series.mean()) / float(series.std(ddof=1))
    skew = float(np.mean(centred**3)) / m2**1.5
    kurt = float(np.mean(centred**4)) / m2**2
    return sr, skew, kurt


def expected_max_sharpe(sr_var: float, trials: int) -> float:
    """SR0: expected maximum per-period Sharpe of `trials` zero-edge trials with
    cross-trial Sharpe variance `sr_var`; 0 when trials is 1; O(1)."""
    if trials < 1:
        raise ValueError("trials must be at least 1")
    if trials == 1:
        return 0.0
    first = _NORMAL.inv_cdf(1.0 - 1.0 / trials)
    second = _NORMAL.inv_cdf(1.0 - 1.0 / (trials * math.e))
    return math.sqrt(sr_var) * ((1.0 - EULER_GAMMA) * first + EULER_GAMMA * second)


def deflated_sharpe(  # noqa: PLR0913 - the paper's five inputs, named
    sr: float,
    *,
    trials: int,
    periods: int,
    skew: float,
    kurt: float,
    sr_var: float | None = None,
) -> float:
    """Deflated Sharpe probability (Bailey and Lopez de Prado 2014); `sr` and
    `sr_var` per period, not annualized; `kurt` raw (3 normal); O(1).

    Returns nan when the term 1 - skew sr + (kurt - 1) / 4 sr^2 is not positive.
    """
    if periods < 2:  # noqa: PLR2004 - sqrt(T - 1) needs two periods
        raise ValueError("periods must be at least 2")
    sr0 = 0.0 if sr_var is None else expected_max_sharpe(sr_var, trials)
    spread = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    if not spread > 0.0:
        return math.nan
    return _NORMAL.cdf((sr - sr0) * math.sqrt(periods - 1) / math.sqrt(spread))


@dataclass(frozen=True, slots=True)
class Regimes:
    """Annualized Sharpe by calendar year (key "2019") and by volatility
    tercile (keys low, mid, high)."""

    by_year: dict[str, float]
    by_vol: dict[str, float]


def vol_terciles(vol_proxy: Floats) -> tuple[Ints, Ints, Ints]:
    """Period indices of the low, mid, high thirds of a volatility proxy by rank;
    NaN periods excluded, sizes differ by at most one, ties stable; O(T log T)."""
    proxy = np.asarray(vol_proxy, dtype=np.float64).reshape(-1)
    present = np.flatnonzero(~np.isnan(proxy)).astype(np.int64)
    ranked = present[np.argsort(proxy[present], kind="stable")]
    low, mid, high = np.array_split(ranked, 3)
    return np.sort(low), np.sort(mid), np.sort(high)


def regime_split(
    returns: Floats,
    *,
    dates_years: Ints,
    vol_proxy: Floats,
    periods_per_year: int = PERIODS_PER_YEAR,
) -> Regimes:
    """Sharpe of per-period returns per calendar year and per vol tercile; the
    caller lags `vol_proxy` so it is known at each period; O(T log T)."""
    series = _series(returns)
    years = np.asarray(dates_years, dtype=np.int64).reshape(-1)
    if years.size != series.size or np.size(vol_proxy) != series.size:
        raise ValueError("returns, dates_years and vol_proxy must align")
    by_year = {
        str(year): sharpe(series[years == year], periods_per_year)
        for year in np.unique(years).tolist()
    }
    thirds = vol_terciles(vol_proxy)
    by_vol = {
        label: sharpe(series[index], periods_per_year)
        for label, index in zip(("low", "mid", "high"), thirds, strict=True)
    }
    return Regimes(by_year, by_vol)
