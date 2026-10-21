"""G9: capacity gates promotion. A strategy whose net Sharpe is flat from 0.1x
to 1x but negative at 1x is blocked by name; a hypothesis registered crowded
is blocked until a decision line overrides it, then blocked on odds until a
superseding hypothesis states them, then promotable.

The synthetic panel plants a persistent per-name drift (`alpha`) that no
factor spans, so trailing return ranks carry a real edge.
"""

from __future__ import annotations

import json
from textwrap import dedent

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


def test_crowded_is_blocked_until_an_override_names_it(synthetic, run, plant, families):
    book = edge_book(synthetic, run, plant, families)
    hypothesis_id = plant(
        book,
        "drift",
        "SIGN = 1.0\n" + DRIFT,
        hypothesis={"capacity_class": "crowded", "mechanism": "planted drift"},
        params={"lookback": 252},
        long_only=True,  # no flips from short to long: trades stay under 2% of ADV
        **EDGE,
    )
    code, document, err = run(["measure", str(book), "drift"])
    assert code == 0, err
    batch(run, book, {"critiques": [critique(document["run_id"])]})
    view = run(["check", str(book), "drift"])[1]
    assert view["standing"] == "blocked"
    assert [b.split(":")[0] for b in view["blockers"]] == ["crowded"]
    override = {
        "kw": ["crowd", "ok"],
        "subject": "drift",
        "action": "override",
        "reason": "capacity ceiling checked by hand",
    }
    batch(run, book, {"decisions": [override]})
    view = run(["check", str(book), "drift"])[1]
    assert (view["standing"], view["blockers"]) == (
        "blocked",
        [f"odds: none registered on {hypothesis_id}"],
    )
    stated = {
        "kw": ["drift", "odds"],
        "strategy": "drift",
        "family_id": "g9",
        "capacity_class": "crowded",
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
    batch(run, book, {"hypotheses": [stated]})
    view = run(["check", str(book), "drift"])[1]
    assert (view["standing"], view["blockers"]) == ("promotable", [])
