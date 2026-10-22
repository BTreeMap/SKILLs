"""G9: capacity gates promotion. A strategy whose net Sharpe is flat from 0.1x
to 1x but negative at 1x is blocked by name; an edge whose curve holds is
blocked on odds until a superseding hypothesis states them at the same kill
date, spending no trial, then promotable; every scorecard tests 0.1x, 1x,
and 20x the cap.

The synthetic panel plants a persistent per-name drift (`alpha`) that no
factor spans, so trailing return ranks carry a real edge.
"""

from __future__ import annotations

import json
from textwrap import dedent

from btm_finance.views import extensions

DRIFT = dedent(
    """
    import numpy as np


    def long_short(names, key):
        known = np.flatnonzero(np.isfinite(key))
        third = known.size // 3
        order = known[np.argsort(key[known], kind="stable")]
        weights = {names[i]: 1.0 for i in order[-third:].tolist()}
        weights.update({names[i]: -1.0 for i in order[:third].tolist()})
        return weights


    def signal(market, params):
        closes = market.close(int(round(params["lookback"])) + 1)
        return long_short(market.names, SIGN * (closes[-1] / closes[0] - 1.0))
    """
)
KILL, LATER = "2099-12-31", "2100-06-30"
EDGE = {"rebalance": "quarterly", "holding_days": 63, "family_id": "g9"}


def batch(run, book, payload):
    code, receipt, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps(payload)
    )
    assert code == 0, err
    return receipt


def critique(run_id: str) -> dict:
    return {
        "kw": ["clean", "read"],
        "run_id": run_id,
        "blockers": [],
        "concerns": [],
        "by": "test",
    }


def edge_book(synthetic, run, plant, families):
    """Two weaker cousins (short lookbacks) measured first: the family PBO ranks
    the candidate's variants against them and DSR counts them."""
    book = synthetic(seed=5, alpha=0.0015)
    families(book, g9={"trials": 20})
    for lookback in (21, 42):
        name = f"near-{lookback}"
        plant(
            book,
            name,
            "SIGN = 1.0\n" + DRIFT,
            params={"lookback": lookback},
            long_only=True,
            **EDGE,
        )
        assert run(["measure", str(book), name])[1]["run_id"]  # refused or not
    return book


def test_flat_but_negative_capacity_is_blocked_by_name(synthetic, run, plant, families):
    book = edge_book(synthetic, run, plant, families)
    plant(book, "fade", "SIGN = -1.0\n" + DRIFT, params={"lookback": 252}, **EDGE)
    code, document, _ = run(["measure", str(book), "fade"])
    assert code == 1  # negative gross: every cost is lost, so cost_share is 1
    small, cap = (
        document["scorecard"]["capacity"]["0.1x"],
        document["scorecard"]["capacity"]["1x"],
    )
    assert cap < 0
    assert abs(cap - small) <= 0.2 * abs(small)  # flat from 0.1x to 1x
    batch(run, book, {"critiques": [critique(document["run_id"])]})
    view = run(["check", str(book), "fade"])[1]
    assert view["standing"] in {"blocked", "discard"}
    assert any("is not positive" in b for b in view["blockers"])


def test_an_edge_is_blocked_on_odds_until_stated(synthetic, run, plant, families):
    book = edge_book(synthetic, run, plant, families)
    hypothesis_id = plant(
        book,
        "drift",
        "SIGN = 1.0\n" + DRIFT,
        hypothesis={"mechanism": "planted drift"},
        params={"lookback": 252},
        long_only=True,  # no flips from short to long: trades stay under 2% of ADV
        **EDGE,
    )
    code, document, err = run(["measure", str(book), "drift"])
    assert code == 0, err
    batch(run, book, {"critiques": [critique(document["run_id"])]})
    assert set(document["scorecard"]["capacity"]) == {"0.1x", "1x", "20x"}
    view = run(["check", str(book), "drift"])[1]
    assert (view["standing"], view["blockers"]) == (
        "blocked",
        [f"odds: none registered on {hypothesis_id}"],
    )
    stated = {
        "kw": ["drift", "odds"],
        "strategy": "drift",
        "family_id": "g9",
        "mechanism": "planted drift",
        "falsifier": "net Sharpe at or below zero out of sample",
        "falsifier_by": "2099-12-31",
        "counterparty": "planted by the test",
        "min_holding_days": 63,
        "odds": {
            "p_win": 0.55,
            "payoff": 1.2,
            "horizon_days": 63,
            "kelly_implied": 0.175,
        },
        "supersedes": hypothesis_id,
    }
    spent = run(["check", str(book)])[1]["families"]["g9"]["trials_used"]
    batch(run, book, {"hypotheses": [stated]})
    view = run(["check", str(book), "drift"])[1]
    assert (view["standing"], view["blockers"]) == ("promotable", [])
    # same kill date: stating odds spends no trial
    assert run(["check", str(book)])[1]["families"]["g9"]["trials_used"] == spent


def test_superseding_a_line_without_a_kill_date_spends_nothing():
    old = {"id": "a", "family_id": "f"}
    same = {"id": "b", "family_id": "f", "supersedes": "a", "falsifier_by": KILL}
    later = {"id": "c", "family_id": "f", "supersedes": "b", "falsifier_by": LATER}
    assert extensions([old, same]) == []
    assert extensions([old, same, later]) == [later]
