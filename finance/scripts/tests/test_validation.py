"""PBO, purged folds, and Newey-West regression: laws and planted signals."""

from __future__ import annotations

import math

import numpy as np
import pytest
from btm_finance.engine import (
    cscv,
    default_lags,
    factor_regression,
    model_label,
    ols_hac,
    pbo,
    purged_folds,
)


def test_pbo_of_pure_noise_is_near_one_half():
    noise = np.random.default_rng(0).normal(0.0, 0.01, (2000, 20))
    assert 0.3 <= pbo(noise) <= 0.7


def test_pbo_of_a_genuine_edge_is_near_zero():
    trials = np.random.default_rng(1).normal(0.0, 0.01, (2000, 20))
    trials[:, 3] += 0.003
    assert pbo(trials) < 0.1


def test_cscv_shape_and_dropped_rows():
    trials = np.random.default_rng(2).normal(0.0, 0.01, (2005, 5))
    result = cscv(trials)
    assert result.logits.shape == (math.comb(16, 8),)
    assert (result.block_size, result.dropped) == (125, 5)
    assert result.pbo == pytest.approx(np.mean(result.logits < 0))


def test_cscv_logit_hand_value():
    # One trial wins every block, in and out of sample: rank N of N, w N/(N+1).
    trials = np.tile(np.array([0.0, 0.0, 0.0]), (8, 1))
    trials += np.array([[1.0, 2.0, 3.0], [-1.0, -2.0, -3.0]] * 4) * 1e-3
    trials[:, 2] += 1e-2
    result = cscv(trials, blocks=4)
    assert np.allclose(result.logits, math.log(3))
    assert result.pbo == 0.0


@pytest.mark.parametrize(
    ("shape", "blocks", "message"),
    [
        ((2000, 1), 16, "N at least 2"),
        ((31, 4), 16, "T at least 2 \\* blocks = 32"),
        ((2000, 4), 15, "even number of blocks"),
    ],
)
def test_pbo_refuses_what_it_cannot_judge(shape, blocks, message):
    with pytest.raises(ValueError, match=message):
        pbo(np.zeros(shape), blocks=blocks)


@pytest.mark.parametrize(
    ("n", "folds", "embargo"), [(100, 5, 3), (103, 4, 0), (10, 10, 2)]
)
def test_purged_folds_laws(n, folds, embargo):
    pairs = purged_folds(n, folds=folds, embargo=embargo)
    assert len(pairs) == folds
    tests = np.concatenate([test for _, test in pairs])
    assert sorted(tests.tolist()) == list(range(n))
    for train, test in pairs:
        assert train.dtype == np.int64
        assert test.dtype == np.int64
        assert np.intersect1d(train, test).size == 0
        assert np.all(np.diff(test) == 1)
        start, stop = test[0], test[-1] + 1
        assert np.all((train < start - embargo) | (train >= stop + embargo))
        allowed = [i for i in range(n) if i < start - embargo or i >= stop + embargo]
        assert train.tolist() == allowed


def test_purged_folds_refuses_bad_arguments():
    with pytest.raises(ValueError, match="folds"):
        purged_folds(10, folds=1, embargo=0)
    with pytest.raises(ValueError, match="embargo"):
        purged_folds(10, folds=2, embargo=-1)


def regression_sample(seed: int, n: int = 2500) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    factors = rng.normal(0.0, 0.01, (n, 2))
    y = 1e-4 + factors @ np.array([0.5, -0.2]) + rng.normal(0.0, 0.001, n)
    return y, factors


def hc0_t(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """White HC0 t-statistics by the textbook sandwich, one row at a time."""
    design = np.column_stack((np.ones(len(y)), x))
    coef = np.linalg.solve(design.T @ design, design.T @ y)
    residual = y - design @ coef
    meat = sum(
        np.outer(row, row) * e**2 for row, e in zip(design, residual, strict=True)
    )
    bread = np.linalg.inv(design.T @ design)
    return coef / np.sqrt(np.diag(bread @ meat @ bread))


def classical_t(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    design = np.column_stack((np.ones(len(y)), x))
    coef = np.linalg.solve(design.T @ design, design.T @ y)
    residual = y - design @ coef
    sigma2 = residual @ residual / (len(y) - design.shape[1])
    return coef / np.sqrt(np.diag(sigma2 * np.linalg.inv(design.T @ design)))


def test_ols_hac_with_zero_lags_is_white_hc0():
    y, x = regression_sample(3, 400)
    fit = ols_hac(y, x, lags=0)
    expected = hc0_t(y, x)
    assert fit.t_alpha == pytest.approx(expected[0], rel=1e-9)
    assert fit.t_betas == pytest.approx(tuple(expected[1:]), rel=1e-9)


def test_ols_hac_with_zero_lags_matches_plain_ols_on_homoskedastic_data():
    y, x = regression_sample(4)
    fit = ols_hac(y, x, lags=0)
    plain = classical_t(y, x)
    assert fit.t_alpha == pytest.approx(plain[0], rel=0.05)
    assert fit.t_betas == pytest.approx(tuple(plain[1:]), rel=0.05)


def test_newey_west_t_within_twenty_percent_of_ols_on_iid_data():
    y, x = regression_sample(5)
    fit = ols_hac(y, x)
    plain = classical_t(y, x)
    assert fit.lags == default_lags(2500) == 8
    assert fit.t_alpha == pytest.approx(plain[0], rel=0.2)
    assert fit.t_betas == pytest.approx(tuple(plain[1:]), rel=0.2)


def test_planted_alpha_is_found():
    y, x = regression_sample(6)
    fit = ols_hac(y, x)
    assert fit.t_alpha > 3.0
    assert 0.0 <= fit.r2 <= 1.0
    assert fit.betas == pytest.approx((0.5, -0.2), abs=0.02)
    assert fit.n == 2500


def test_factor_regression_annualizes_and_names():
    y, x = regression_sample(7)
    fit = factor_regression(y, x, ("Mkt-RF", "SMB"), 252)
    assert fit.alpha_annual == pytest.approx(ols_hac(y, x).alpha * 252)
    assert set(fit.loadings) == {"Mkt-RF", "SMB"}
    assert fit.model == "mktrf+smb"


@pytest.mark.parametrize(
    ("names", "label"),
    [
        (("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"), "ff5+mom"),
        (("Mkt-RF", "SMB", "HML", "UMD"), "ff3+mom"),
        (("mkt_rf", "smb", "hml", "rmw", "cma", "QMJ", "BAB"), "ff5+bab+qmj"),
    ],
)
def test_model_label(names, label):
    assert model_label(names) == label
