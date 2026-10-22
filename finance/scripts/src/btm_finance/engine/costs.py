"""Trading costs: high-low spread estimators, square-root impact, net returns,
capacity curve. Pure numpy; costs are proportional decimals, not bps or %."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from btm_finance.engine.metrics import PERIODS_PER_YEAR, Floats, sharpe

BPS = 1e-4
# 3 - 2 sqrt(2), the Corwin-Schultz denominator.
_CS_K = 3.0 - 2.0 * math.sqrt(2.0)


@dataclass(frozen=True, slots=True, eq=False)
class Spread:
    """T by N proportional bid-ask spread estimates, decimal; NaN where a name
    lacks a pair of days. `half` is what a one-way trade pays."""

    full: Floats

    @property
    def half(self) -> Floats:
        """Half-spread, the one-way proportional cost."""
        return self.full / 2.0


def _panel(values: Floats) -> Floats:
    """T by N float64 view; a 1D series is one name."""
    array = np.asarray(values, dtype=np.float64)
    return array[:, None] if array.ndim == 1 else array


def _lagged_pair(today: Floats) -> Floats:
    """Row t holds the pair (t - 1, t); row 0 is NaN, so no estimate looks ahead."""
    out = np.full((today.shape[0] + 1, *today.shape[1:]), np.nan)
    out[1:] = today
    return out


def corwin_schultz(high: Floats, low: Floats) -> Spread:
    """Corwin and Schultz (2012) two-day spread, row t from days t - 1 and t,
    negatives set to 0; daily highs and lows T by N, NaN propagates; O(T N)."""
    hi, lo = _panel(high), _panel(low)
    with np.errstate(invalid="ignore", divide="ignore"):
        range_sq = np.log(hi / lo) ** 2
        beta = range_sq[:-1] + range_sq[1:]
        gamma = np.log(np.maximum(hi[:-1], hi[1:]) / np.minimum(lo[:-1], lo[1:])) ** 2
        alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / _CS_K - np.sqrt(gamma / _CS_K)
        spread = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
    spread[spread < 0.0] = 0.0
    return Spread(_lagged_pair(spread))


def abdi_ranaldo_terms(high: Floats, low: Floats, close: Floats) -> Floats:
    """Per-pair Abdi and Ranaldo (2017) term (c_t - eta_t)(c_t - eta_t+1), logs,
    eta the mid-range; row t from days t - 1 and t; T by N, NaN propagates; O(T N)."""
    hi, lo, last = _panel(high), _panel(low), _panel(close)
    with np.errstate(invalid="ignore", divide="ignore"):
        mid = (np.log(hi) + np.log(lo)) / 2.0
        log_close = np.log(last)
    return _lagged_pair((log_close[:-1] - mid[:-1]) * (log_close[:-1] - mid[1:]))


def _ar_spread(term: Floats) -> Floats:
    """Spread 2 sqrt(max(term, 0)), NaN kept."""
    return 2.0 * np.sqrt(np.where(term < 0.0, 0.0, term))


def abdi_ranaldo(high: Floats, low: Floats, close: Floats) -> Spread:
    """Two-day Abdi and Ranaldo spread 2 sqrt(max(term, 0)) per pair; noisy, use
    `abdi_ranaldo_window` for a level; O(T N)."""
    return Spread(_ar_spread(abdi_ranaldo_terms(high, low, close)))


def abdi_ranaldo_window(
    high: Floats, low: Floats, close: Floats, *, window: int
) -> Spread:
    """Abdi and Ranaldo spread over a trailing window: 2 sqrt(max(mean term, 0)),
    the paper's averaging; T by N, decimal; O(T N)."""
    return Spread(
        _ar_spread(rolling_mean(abdi_ranaldo_terms(high, low, close), window))
    )


def rolling_mean(estimates: Floats, window: int) -> Floats:
    """Trailing mean over `window` rows ignoring NaN; NaN before the window fills
    or when every value in it is NaN; T by N in, T by N out; O(T N)."""
    if window < 1:
        raise ValueError("window must be at least 1")
    values = _panel(estimates)
    present = ~np.isnan(values)
    sums = np.cumsum(np.where(present, values, 0.0), axis=0)
    counts = np.cumsum(present, axis=0, dtype=np.float64)
    sums[window:] -= sums[:-window].copy()
    counts[window:] -= counts[:-window].copy()
    out: Floats = np.divide(
        sums, counts, out=np.full_like(sums, np.nan), where=counts > 0
    )
    out[: window - 1] = np.nan
    return out


def sqrt_impact(
    coefficient: float, daily_vol: Floats | float, participation: Floats | float
) -> Floats:
    """Square-root impact coefficient * daily_vol * sqrt(participation), the
    proportional cost per trade; elementwise, decimal inputs; O(size)."""
    return np.asarray(
        coefficient * np.asarray(daily_vol) * np.sqrt(np.asarray(participation)),
        dtype=np.float64,
    )


def net_returns(
    gross: Floats,
    trades: Floats,
    *,
    half_spread: Floats,
    commission_bps: Floats | float,
    impact: Floats | float = 0.0,
) -> Floats:
    """Per-period net return: gross minus sum over names of trades * (half_spread
    + commission + impact); trades T by N absolute weight change, commission
    one number or one per name; O(T N).

    Untraded names cost nothing; a traded name with NaN cost gives NaN.
    """
    returns = np.asarray(gross, dtype=np.float64).reshape(-1)
    traded = np.nan_to_num(_panel(trades), nan=0.0)
    if traded.shape[0] != returns.size:
        raise ValueError("trades must have one row per gross return")
    rate = np.broadcast_to(
        np.asarray(half_spread, dtype=np.float64) + commission_bps * BPS + impact,
        traded.shape,
    )
    cost = np.where(traded == 0.0, 0.0, traded * rate).sum(axis=1)
    return np.asarray(returns - cost, dtype=np.float64)


def capacity_curve(  # noqa: PLR0913 - every cost input is a separate panel
    gross: Floats,
    trades: Floats,
    adv_dollar: Floats,
    *,
    capital_levels: tuple[float, ...],
    daily_vol: Floats,
    half_spread: Floats,
    commission_bps: Floats | float,
    impact_coefficient: float,
    periods_per_year: int = PERIODS_PER_YEAR,
) -> tuple[float, ...]:
    """Annualized net Sharpe per capital level, participation = capital * trades
    / adv_dollar, square-root impact on; capital and ADV in dollars; O(L T N).

    Raises ValueError when a traded name has zero or NaN ADV.
    """
    traded = np.nan_to_num(_panel(trades), nan=0.0)
    adv = np.broadcast_to(_panel(adv_dollar), traded.shape)
    if np.any((traded != 0.0) & ~(adv > 0.0)):
        raise ValueError("adv_dollar must be positive wherever trades are nonzero")
    levels = []
    for capital in capital_levels:
        with np.errstate(invalid="ignore", divide="ignore"):
            participation = np.where(traded == 0.0, 0.0, capital * traded / adv)
        impact = sqrt_impact(impact_coefficient, daily_vol, participation)
        net = net_returns(
            gross,
            traded,
            half_spread=half_spread,
            commission_bps=commission_bps,
            impact=impact,
        )
        levels.append(sharpe(net, periods_per_year))
    return tuple(levels)
