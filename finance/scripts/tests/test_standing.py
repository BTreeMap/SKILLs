"""Standing, pure: DSR and PBO blockers named with value and limit, the
capacity rule, and the odds blocker that keeps a clean run from reading
promotable without stated odds."""

from __future__ import annotations

import pytest
from btm_finance.models import Limits, Status, limits_template
from btm_finance.standing import Evidence, Standing, standing_of

LIMITS = Limits.model_validate(limits_template(10_000_000))
ODDS = {"p_win": 0.55, "payoff": 1.2, "horizon_days": 63, "kelly_implied": 0.175}
CURVE = {"0.1x": 1.0, "1x": 0.95, "20x": 0.2}


def evidence(
    dsr: float,
    pbo: float,
    *,
    odds: dict | None = ODDS,
    status: Status = Status.RESEARCH,
    curve: dict | None = None,
) -> Evidence:
    """Every gate but DSR and PBO clear: t_alpha, capacity, bounds, trials,
    critique."""
    card = {
        "dsr": dsr,
        "pbo": pbo,
        "trials": 1,
        "factor": {"t_alpha": 4.0},
        "capacity": curve or CURVE,
        "cost_share": 0.1,
        "adv_participation_max": 0.01,
        "min_holding_days_realized": 21,
    }
    hypothesis = {"id": "h1"}
    return Evidence(
        strategy="drift",
        run={
            "run_id": "r1",
            "hypothesis_id": "h1",
            "family_id": "baseline",
            "scorecard": card,
            "reasons": {},
            "config": {"holding_days": 21},
        },
        hypothesis=hypothesis if odds is None else hypothesis | {"odds": odds},
        critique={"id": "c1", "blockers": []},
        status=status,
        raw_status=status.value,
    )


def test_dsr_085_and_pbo_02_read_blocked_with_both_blockers_named():
    view = standing_of(evidence(0.85, 0.2), LIMITS)
    assert view.standing is Standing.BLOCKED
    assert view.blockers == ("dsr: 0.85 vs 0.95", "pbo: 0.2 vs 0.1")


def test_clearing_every_gate_still_reads_promotable():
    view = standing_of(evidence(0.97, 0.05), LIMITS)
    assert (view.standing, view.blockers) == (Standing.PROMOTABLE, ())


def test_a_scalable_curve_needs_no_override():
    flat = {"0.1x": 1.0, "1x": 0.99, "20x": 0.98}
    view = standing_of(evidence(0.97, 0.05, curve=flat), LIMITS)
    assert (view.standing, view.blockers) == (Standing.PROMOTABLE, ())


@pytest.mark.parametrize(
    ("curve", "blocked"),
    [
        ({"0.1x": 1.0, "1x": 0.79, "20x": 0.1}, True),  # 21% below 0.1x
        ({"0.1x": 1.0, "1x": 0.81, "20x": -0.5}, False),  # 20x reported only
        ({"0.1x": 0.5, "1x": 0.9, "20x": 0.9}, False),  # above 0.1x: no gate
        ({"0.1x": -0.1, "1x": -0.1, "20x": -0.1}, True),  # 1x not positive
    ],
)
def test_capacity_blocks_1x_too_far_below_01x_or_not_positive(curve, blocked):
    view = standing_of(evidence(0.97, 0.05, curve=curve), LIMITS)
    found = [b for b in view.blockers if b.startswith("capacity")]
    assert bool(found) is blocked, found


def test_a_live_sleeve_reads_its_standing_and_a_retired_one_blocks():
    assert standing_of(evidence(0.97, 0.05, status=Status.LIVE), LIMITS).blockers == ()
    retired = standing_of(evidence(0.97, 0.05, status=Status.RETIRED), LIMITS)
    assert retired.blockers == ("status: retired",)


@pytest.mark.parametrize(("dsr", "pbo"), [(0.97, 0.05)])
def test_no_odds_blocks_what_would_be_promotable(dsr, pbo):
    view = standing_of(evidence(dsr, pbo, odds=None), LIMITS)
    assert view.standing is Standing.BLOCKED
    assert view.blockers[-1] == "odds: none registered on h1"


def test_no_odds_adds_nothing_when_another_gate_blocks():
    view = standing_of(evidence(0.5, 0.3, odds=None), LIMITS)
    assert not any(b.startswith("odds") for b in view.blockers)
