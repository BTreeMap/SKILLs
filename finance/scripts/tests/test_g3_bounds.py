"""G3: only slow-money edges pass. A holding period under the floor is
refused by name before running; a strategy that churns its whole book every
rebalance still writes its run line, marked refused, and exits 1. A weight
past the ADV bound is clipped to it and counted, never refused."""

from __future__ import annotations

import json
from textwrap import dedent

CHURN = dedent(
    '''
    import numpy as np


    def signal(market, params):
        """Long one half, short the other, swapping halves every month."""
        names = market.names
        flip = 1.0 if int(market.day / 30.4375) % 2 else -1.0
        half = len(names) // 2
        return {name: flip if i < half else -flip for i, name in enumerate(names)}
'''
)


OVERSIZE = dedent(
    '''
    def signal(market, params):
        """One name a hundred times every other."""
        names = market.names
        return {name: 100.0 if i == 0 else 1.0 for i, name in enumerate(names)}
'''
)


def edit_limits(book, **sizing):
    """The operator's edit of `limits.json`: top-level keys, `sizing` keys."""
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["adv_multiple"] = sizing.pop("adv_multiple", limits["adv_multiple"])
    limits["sizing"] |= sizing
    path.write_text(json.dumps(limits))


def test_a_two_day_holding_is_refused_before_running(book, run, plant):
    plant(book, "fast", "def signal(market, params):\n    return {}\n", holding_days=2)
    code, document, err = run(["measure", str(book), "fast"])
    assert code == 1
    assert document is None
    assert "holding_days 2 is under limits.min_holding_days 5" in err
    assert (book / "ledger" / "runs.jsonl").read_text() == ""


def test_a_churning_book_is_refused_after_running_and_still_counts(
    synthetic, run, plant
):
    book = synthetic(seed=3)
    plant(book, "churn", CHURN)
    code, document, err = run(["measure", str(book), "churn"])
    assert code == 1
    assert "error: refused cost_share" in err
    assert document["refused"][0].startswith("cost_share: ")
    lines = (book / "ledger" / "runs.jsonl").read_text().splitlines()
    line = json.loads(lines[-1])
    assert line["refused"] == document["refused"]
    assert line["scorecard"]["cost_share"] > 0.25
    view = run(["check", str(book)])[1]
    assert view["families"]["baseline"]["trials_used"] == 1


def test_an_oversize_weight_is_clipped_to_the_adv_bound_and_counted(
    synthetic, run, plant
):
    book = synthetic(seed=3)
    edit_limits(book, max_weight=1.0, adv_multiple=0.001)
    plant(book, "big", OVERSIZE)
    code, document, err = run(["measure", str(book), "big"])
    assert code == 0, err
    card = document["scorecard"]
    assert document["refused"] == []
    assert card["adv_clipped"] > 0
    assert 0.0 < card["adv_clipped_share"] < 1.0
    line = json.loads((book / "ledger" / "runs.jsonl").read_text().splitlines()[-1])
    assert line["refused"] == []
    assert line["scorecard"]["adv_clipped"] == card["adv_clipped"]


def test_the_scaffolded_baseline_measures_under_the_template_max_weight(synthetic, run):
    book = synthetic(seed=11)
    edit_limits(book, max_weight=0.10)
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    assert document["refused"] == []
