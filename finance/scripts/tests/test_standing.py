"""Standing, pure: the probe tier between blocked and promotable, and the
odds blocker that keeps both from reading without stated odds."""

from __future__ import annotations

from datetime import date

import pytest
from btm_finance.models import Limits, Status, limits_template
from btm_finance.standing import Evidence, Standing, standing_of

LIMITS = Limits.model_validate(limits_template(10_000_000))
ODDS = {"p_win": 0.55, "payoff": 1.2, "horizon_days": 63, "kelly_implied": 0.175}


def evidence(
    dsr: float,
    pbo: float,
    *,
    odds: dict | None = ODDS,
    status: Status = Status.RESEARCH,
) -> Evidence:
    """Every gate but DSR and PBO clear: t_alpha, capacity, bounds, trials,
    critique."""
    card = {
        "dsr": dsr,
        "pbo": pbo,
        "trials": 1,
        "factor": {"t_alpha": 4.0},
        "capacity": {"0.1x": 1.0, "1x": 0.95, "20x": 0.2},
        "cost_share": 0.1,
        "adv_participation_max": 0.01,
        "min_holding_days_realized": 21,
    }
    hypothesis = {"id": "h1", "capacity_class": "in_band"}
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
        decisions=(),
        status=status,
        raw_status=status.value,
        today=date(2026, 10, 21),
    )


def test_dsr_085_and_pbo_02_read_probe_with_both_blockers_named():
    view = standing_of(evidence(0.85, 0.2), LIMITS)
    assert view.standing is Standing.PROBE
    assert view.blockers == ("dsr: 0.85 vs 0.95", "pbo: 0.2 vs 0.1")
    assert "probe" in view.next and "0.02" in view.next


@pytest.mark.parametrize(("dsr", "pbo"), [(0.79, 0.2), (0.85, 0.25)])
def test_below_the_probe_thresholds_reads_blocked(dsr, pbo):
    assert standing_of(evidence(dsr, pbo), LIMITS).standing is Standing.BLOCKED


def test_a_running_probe_is_told_what_paper_or_live_needs():
    view = standing_of(evidence(0.85, 0.2, status=Status.PROBE), LIMITS)
    assert view.standing is Standing.PROBE
    assert "paper or live needs dsr 0.95" in view.next


def test_clearing_every_gate_still_reads_promotable():
    view = standing_of(evidence(0.97, 0.05), LIMITS)
    assert (view.standing, view.blockers) == (Standing.PROMOTABLE, ())


@pytest.mark.parametrize(("dsr", "pbo"), [(0.97, 0.05), (0.85, 0.2)])
def test_no_odds_blocks_what_would_be_promotable_or_probe(dsr, pbo):
    view = standing_of(evidence(dsr, pbo, odds=None), LIMITS)
    assert view.standing is Standing.BLOCKED
    assert view.blockers[-1] == "odds: none registered on h1"


def test_no_odds_adds_nothing_when_another_gate_blocks():
    view = standing_of(evidence(0.5, 0.3, odds=None), LIMITS)
    assert not any(b.startswith("odds") for b in view.blockers)
