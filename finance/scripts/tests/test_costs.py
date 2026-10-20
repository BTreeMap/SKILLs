"""Spread estimators on a simulated Roll market, impact, net returns, capacity."""

from __future__ import annotations

import math
import warnings
from itertools import pairwise

import numpy as np
import pytest
from btm_finance.engine import (
    abdi_ranaldo,
    abdi_ranaldo_terms,
    abdi_ranaldo_window,
    capacity_curve,
    corwin_schultz,
    net_returns,
    rolling_mean,
    sharpe,
    sqrt_impact,
)

SPREAD = 0.01


def roll_market(
    seed: int, *, days: int = 2000, names: int = 3, ticks: int = 78
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Daily high, low, close of a Roll model: log mid a random walk with daily
    vol 1%, every trade at the bid or ask, `ticks` trades a day."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 0.01 / math.sqrt(ticks), (days * ticks, names))
    side = rng.choice(np.array([-1.0, 1.0]), (days * ticks, names))
    prices = np.exp(np.cumsum(steps, axis=0) + side * SPREAD / 2)
    prices = prices.reshape(days, ticks, names)
    return prices.max(axis=1), prices.min(axis=1), prices[:, -1, :]


def test_corwin_schultz_hand_value():
    high, low = np.array([101.0, 102.0]), np.array([99.0, 100.0])
    beta = math.log(101 / 99) ** 2 + math.log(102 / 100) ** 2
    gamma = math.log(102 / 99) ** 2
    k = 3 - 2 * math.sqrt(2)
    alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / k - math.sqrt(gamma / k)
    expected = max(2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha)), 0.0)
    got = corwin_schultz(high, low)
    assert math.isnan(got.full[0, 0])
    assert got.full[1, 0] == pytest.approx(expected)
    assert got.half[1, 0] == pytest.approx(expected / 2)


def test_corwin_schultz_floors_negative_estimates_at_zero():
    # A wide two-day range against narrow daily ranges drives alpha negative.
    got = corwin_schultz(np.array([100.5, 110.5]), np.array([99.5, 109.5]))
    assert got.full[1, 0] == 0.0


def test_abdi_ranaldo_term_hand_value():
    high, low = np.array([[102.0], [104.0]]), np.array([[98.0], [100.0]])
    close = np.array([[101.0], [103.0]])
    eta0 = (math.log(102) + math.log(98)) / 2
    eta1 = (math.log(104) + math.log(100)) / 2
    term = (math.log(101) - eta0) * (math.log(101) - eta1)
    assert abdi_ranaldo_terms(high, low, close)[1, 0] == pytest.approx(term)
    expected = 2 * math.sqrt(max(term, 0.0))
    assert abdi_ranaldo(high, low, close).full[1, 0] == pytest.approx(expected)


def test_corwin_schultz_recovers_the_planted_spread():
    high, low, _ = roll_market(3)
    level = rolling_mean(corwin_schultz(high, low).full, 250)[-1]
    assert np.allclose(level, SPREAD, rtol=0.25)


def test_abdi_ranaldo_recovers_the_planted_spread():
    high, low, close = roll_market(3)
    level = abdi_ranaldo_window(high, low, close, window=250).full[-1]
    assert np.allclose(level, SPREAD, rtol=0.25)
    sparse = abdi_ranaldo_window(*roll_market(4, ticks=8), window=250).full[-1]
    assert np.allclose(sparse, SPREAD, rtol=0.25)


def test_missing_days_propagate_as_nan_without_warning():
    high, low, close = roll_market(5, days=40)
    for panel in (high, low, close):
        panel[10, 0] = math.nan
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        cs = corwin_schultz(high, low).full
        ar = abdi_ranaldo(high, low, close).full
    for estimate in (cs, ar):
        assert np.isnan(estimate[[10, 11], 0]).all()
        assert not np.isnan(estimate[1:10, 0]).any()
        assert not np.isnan(estimate[1:, 1:]).any()


def test_rolling_mean_skips_nan_and_waits_for_the_window():
    values = np.array([[1.0], [math.nan], [3.0], [5.0], [math.nan], [math.nan]])
    got = rolling_mean(values, 2)[:, 0]
    assert math.isnan(got[0])
    assert got[1:4].tolist() == [1.0, 3.0, 4.0]
    assert got[4] == 5.0
    assert math.isnan(got[5])


def test_sqrt_impact_hand_value_and_broadcast():
    assert float(sqrt_impact(0.1, 0.02, 0.01)) == pytest.approx(2e-4)
    got = sqrt_impact(0.1, np.array([0.02, 0.04]), np.array([[0.01], [0.04]]))
    assert got.shape == (2, 2)
    assert got[1, 1] == pytest.approx(0.1 * 0.04 * 0.2)


def test_net_equals_gross_without_trades():
    gross = np.random.default_rng(6).normal(0.0, 0.01, 50)
    trades = np.zeros((50, 3))
    spread = np.full(3, math.nan)
    net = net_returns(gross, trades, half_spread=spread, commission_bps=1.0)
    assert np.array_equal(net, gross)


def test_net_returns_hand_value():
    gross = np.array([0.01, 0.02])
    trades = np.array([[0.1, 0.0], [0.2, 0.3]])
    spread = np.array([0.002, 0.004])
    net = net_returns(
        gross, trades, half_spread=spread, commission_bps=10.0, impact=0.001
    )
    # costs: 0.1 * 0.004 then 0.2 * 0.004 + 0.3 * 0.006.
    assert net == pytest.approx([0.01 - 0.0004, 0.02 - 0.0008 - 0.0018])


def capacity_inputs(seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    days, names = 750, 20
    return {
        "gross": rng.normal(0.0008, 0.01, days),
        "trades": np.abs(rng.normal(0.0, 0.02, (days, names))),
        "adv_dollar": rng.uniform(5e6, 5e7, (days, names)),
        "daily_vol": rng.uniform(0.01, 0.03, (days, names)),
        "half_spread": rng.uniform(0.0005, 0.003, names),
    }


def test_net_sharpe_is_non_increasing_in_capital():
    inputs = capacity_inputs(8)
    levels = (1e5, 1e6, 1e7, 1e8, 2e8, 1e9)
    curve = capacity_curve(
        inputs["gross"],
        inputs["trades"],
        inputs["adv_dollar"],
        capital_levels=levels,
        daily_vol=inputs["daily_vol"],
        half_spread=inputs["half_spread"],
        commission_bps=1.0,
        impact_coefficient=0.1,
    )
    assert len(curve) == len(levels)
    assert all(later <= earlier for earlier, later in pairwise(curve))
    assert curve[0] < sharpe(inputs["gross"])


def test_capacity_curve_with_zero_trades_is_gross_sharpe():
    inputs = capacity_inputs(9)
    curve = capacity_curve(
        inputs["gross"],
        np.zeros_like(inputs["trades"]),
        np.zeros_like(inputs["adv_dollar"]),
        capital_levels=(1e6, 1e8),
        daily_vol=inputs["daily_vol"],
        half_spread=inputs["half_spread"],
        commission_bps=1.0,
        impact_coefficient=0.1,
    )
    assert curve == pytest.approx((sharpe(inputs["gross"]),) * 2, rel=1e-12)


def test_capacity_curve_refuses_traded_names_without_adv():
    inputs = capacity_inputs(10)
    inputs["adv_dollar"][5, 2] = math.nan
    with pytest.raises(ValueError, match="adv_dollar"):
        capacity_curve(
            inputs["gross"],
            inputs["trades"],
            inputs["adv_dollar"],
            capital_levels=(1e6,),
            daily_vol=inputs["daily_vol"],
            half_spread=inputs["half_spread"],
            commission_bps=1.0,
            impact_coefficient=0.1,
        )
