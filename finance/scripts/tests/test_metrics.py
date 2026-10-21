"""Return-series metrics against hand-computed values and the laws they owe."""

from __future__ import annotations

import math
from itertools import pairwise
from statistics import NormalDist

import numpy as np
import pytest
from btm_finance.engine import (
    annualized_return,
    annualized_vol,
    cost_share,
    deflated_sharpe,
    expected_max_sharpe,
    max_drawdown,
    regime_split,
    ruin_loss,
    sharpe,
    sr_moments,
    turnover_annual,
    vol_terciles,
)

NORMAL = NormalDist()


def test_sharpe_matches_mean_over_sample_std_annualized():
    sample = np.random.default_rng(11).normal(0.0004, 0.01, 5000)
    expected = sample.mean() / sample.std(ddof=1) * math.sqrt(252)
    assert sharpe(sample) == pytest.approx(expected, rel=1e-12, abs=1e-12)


@pytest.mark.parametrize(
    ("value", "expected"), [(0.001, math.inf), (-0.001, -math.inf)]
)
def test_sharpe_of_a_constant_series_is_signed_infinity(value, expected):
    assert sharpe(np.full(300, value)) == expected


def test_sharpe_of_a_zero_series_and_of_one_period_is_nan():
    assert math.isnan(sharpe(np.zeros(300)))
    assert math.isnan(sharpe(np.array([0.01])))


def test_sharpe_refuses_nan():
    with pytest.raises(ValueError, match="NaN-free"):
        sharpe(np.array([0.01, math.nan, 0.02]))


def test_annualized_return_compounds():
    # 1% per period for 252 periods compounds to 1.01**252 - 1.
    assert annualized_return(np.full(252, 0.01)) == pytest.approx(1.01**252 - 1)
    assert annualized_return(np.full(504, 0.01)) == pytest.approx(1.01**252 - 1)


def test_annualized_vol_scales_by_root_periods():
    sample = np.array([0.01, -0.01, 0.02, 0.0])
    assert annualized_vol(sample, 12) == pytest.approx(
        sample.std(ddof=1) * math.sqrt(12)
    )


def test_max_drawdown_hand_value():
    # wealth 1, 1.1, 0.55, 0.66: worst fall is 1.1 to 0.55, one half.
    assert max_drawdown(np.array([0.1, -0.5, 0.2])) == pytest.approx(0.5)
    assert max_drawdown(np.array([0.01, 0.02])) == 0.0


def test_turnover_annual_hand_value():
    weights = np.array([[0.0, 0.0], [0.5, 0.5], [0.5, 0.5]])
    # one-way 0.5 then 0, mean 0.25 per period.
    assert turnover_annual(weights, 252) == pytest.approx(63.0)
    with_gap = np.array([[0.0, math.nan], [0.5, 0.5], [0.5, 0.5]])
    assert turnover_annual(with_gap, 252) == pytest.approx(63.0)


def test_cost_share_hand_values_and_clip():
    assert cost_share(np.array([0.01, 0.01]), np.array([0.005, 0.005])) == 0.5
    assert cost_share(np.array([0.01]), np.array([0.02])) == 0.0
    assert cost_share(np.array([0.01]), np.array([-0.05])) == 1.0
    assert cost_share(np.array([-0.01]), np.array([-0.02])) == 1.0
    assert cost_share(np.array([-0.01]), np.array([-0.01])) == 0.0


def test_sr_moments_hand_values():
    sr, skew, kurt = sr_moments(np.array([1.0, 2.0, 3.0, 4.0]))
    assert sr == pytest.approx(2.5 / math.sqrt(5 / 3))
    assert skew == pytest.approx(0.0)
    # centred +-1.5, +-0.5: m2 1.25, m4 2.5625, raw kurtosis 1.64.
    assert kurt == pytest.approx(1.64)


def test_raw_kurtosis_of_a_large_normal_is_near_three():
    _, skew, kurt = sr_moments(np.random.default_rng(3).normal(size=200_000))
    assert abs(skew) < 0.02
    assert kurt == pytest.approx(3.0, abs=0.05)


def test_deflated_sharpe_is_one_half_at_zero_edge_one_trial():
    value = deflated_sharpe(0.0, trials=1, periods=500, skew=0.0, kurt=3.0)
    assert value == 0.5


def test_deflated_sharpe_hand_value_one_trial():
    # PSR(0): Phi(0.05 sqrt(999) / sqrt(1 + (3 - 1) / 4 * 0.0025)).
    expected = NORMAL.cdf(0.05 * math.sqrt(999) / math.sqrt(1.00125))
    got = deflated_sharpe(0.05, trials=1, periods=1000, skew=0.0, kurt=3.0)
    assert got == pytest.approx(expected, rel=1e-12)


def test_expected_max_sharpe_hand_value():
    gamma = 0.5772156649015329
    expected = 0.1 * (
        (1 - gamma) * NORMAL.inv_cdf(0.9)
        + gamma * NORMAL.inv_cdf(1 - 1 / (10 * math.e))
    )
    assert expected_max_sharpe(0.01, 10) == pytest.approx(expected, rel=1e-12)
    assert expected_max_sharpe(0.01, 1) == 0.0


def test_deflated_sharpe_decreases_in_trials():
    values = [
        deflated_sharpe(0.08, trials=n, periods=2000, skew=0, kurt=3, sr_var=4e-4)
        for n in (1, 2, 5, 10, 100, 1000)
    ]
    assert all(later < earlier for earlier, later in pairwise(values))


def best_of_noise(seed: int) -> tuple[np.ndarray, float]:
    """The best of 100 zero-edge trials over 2000 days, and the trials' SR var."""
    noise = np.random.default_rng(seed).normal(0.0, 0.01, (2000, 100))
    ratios = noise.mean(axis=0) / noise.std(axis=0, ddof=1)
    return noise[:, int(np.argmax(ratios))], float(ratios.var(ddof=1))


def test_planted_edge_survives_deflation():
    _, sr_var = best_of_noise(5)
    value = deflated_sharpe(
        0.1, trials=100, periods=2000, skew=0.0, kurt=3.0, sr_var=sr_var
    )
    assert value > 0.95


def test_best_of_noise_is_deflated_below_threshold():
    best, sr_var = best_of_noise(5)
    sr, skew, kurt = sr_moments(best)
    undeflated = deflated_sharpe(sr, trials=1, periods=2000, skew=skew, kurt=kurt)
    value = deflated_sharpe(
        sr, trials=100, periods=2000, skew=skew, kurt=kurt, sr_var=sr_var
    )
    assert undeflated > 0.95
    assert value < 0.95


def test_vol_terciles_partition_the_present_periods():
    proxy = np.random.default_rng(9).normal(size=31)
    proxy[[4, 17]] = math.nan
    low, mid, high = vol_terciles(proxy)
    sizes = [low.size, mid.size, high.size]
    assert max(sizes) - min(sizes) <= 1
    joined = np.concatenate((low, mid, high))
    assert sorted(joined.tolist()) == [i for i in range(31) if i not in (4, 17)]
    assert proxy[low].max() <= proxy[mid].min()
    assert proxy[mid].max() <= proxy[high].min()


def test_regime_split_keys_and_values():
    rng = np.random.default_rng(4)
    returns = rng.normal(0.0005, 0.01, 30)
    years = np.repeat(np.array([2019, 2020, 2021]), 10)
    proxy = np.arange(30, dtype=np.float64)
    split = regime_split(returns, dates_years=years, vol_proxy=proxy)
    assert list(split.by_year) == ["2019", "2020", "2021"]
    assert split.by_year["2020"] == pytest.approx(sharpe(returns[10:20]))
    assert list(split.by_vol) == ["low", "mid", "high"]
    assert split.by_vol["high"] == pytest.approx(sharpe(returns[20:]))


def test_ruin_loss_of_a_constant_path_is_its_compounded_fall():
    # Every row equal: any resample compounds the same 252 days.
    rows = np.full((300, 2), -0.001)
    found = ruin_loss(rows, np.array([0.5, 0.5]), seed=1)
    assert found == pytest.approx(1.0 - 0.999**252)
    assert ruin_loss(rows, np.zeros(2), seed=1) == pytest.approx(0.0)


def test_ruin_loss_is_seeded_and_joint():
    rng = np.random.default_rng(0)
    one = rng.normal(0.0, 0.02, 400)
    # A sleeve and its mirror at equal weight cancel row by row.
    hedged = np.column_stack((one, -one))
    assert ruin_loss(hedged, np.array([0.5, 0.5]), seed=9) == pytest.approx(0.0)
    alone = one[:, None]
    first = ruin_loss(alone, np.array([1.0]), seed=9)
    assert first == ruin_loss(alone, np.array([1.0]), seed=9)
    assert first != ruin_loss(alone, np.array([1.0]), seed=10)
    assert first > ruin_loss(alone, np.array([0.5]), seed=9)
