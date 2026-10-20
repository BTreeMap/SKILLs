"""G3: only slow-money edges score. A holding period under the floor is
refused by name before running; a strategy that churns its whole book every
rebalance still writes its run line, marked refused, and exits 1."""

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


def test_a_two_day_holding_is_refused_before_running(book, run, plant):
    plant(book, "fast", "def signal(market, params):\n    return {}\n", holding_days=2)
    code, document, err = run(["score", str(book), "fast"])
    assert code == 1
    assert document is None
    assert "holding_days 2 is under limits.min_holding_days 5" in err
    assert not (book / "ledger" / "runs.jsonl").exists()


def test_a_churning_book_is_refused_after_running_and_still_counts(
    synthetic, run, plant
):
    book = synthetic(seed=3)
    plant(book, "churn", CHURN)
    code, document, err = run(["score", str(book), "churn"])
    assert code == 1
    assert "error: refused cost_share" in err
    assert document["refused"][0].startswith("cost_share: ")
    lines = (book / "ledger" / "runs.jsonl").read_text().splitlines()
    line = json.loads(lines[-1])
    assert line["refused"] == document["refused"]
    assert line["scorecard"]["cost_share"] > 0.25
    view = run(["check", str(book)])[1]
    assert view["families"]["baseline"]["trials_used"] == 1
