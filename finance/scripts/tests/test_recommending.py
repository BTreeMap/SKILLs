"""The sizing law and the live book's pool, on hand-computed numbers."""

from __future__ import annotations

import math

import pytest
from btm_finance.models import Sizing
from btm_finance.recommending import (
    Account,
    Candidate,
    Quote,
    combined,
    diff,
    live_held,
    replay,
    sleeve_weights,
)

SIZING = Sizing(vol_target=0.10, kelly_fraction=0.25, max_weight=0.05)


def sleeve(name: str, sharpe: float | None, vol: float | None, **weights: float):
    return Candidate(
        strategy=name,
        account=Account.PAPER,
        run_id=f"{name}-run",
        sharpe_net=sharpe,
        vol_net=vol,
        max_drawdown=None,
        half_spread=0.0,
        code_changed=False,
        unknown=0,
        signal={},
        weights=weights,
    )


def test_weight_is_the_smaller_of_vol_target_and_kelly_then_scaled():
    # a: vol 0.20 gives 0.5, Kelly 0.25 * 0.4 / 0.2 = 0.5; b: vol 0.05 gives
    # 2.0, Kelly 0.25 * 0.2 / 0.05 = 1.0; c: no Sharpe, no weight. Sum 1.5.
    found = sleeve_weights(
        [sleeve("a", 0.4, 0.20), sleeve("b", 0.2, 0.05), sleeve("c", None, 0.1)],
        SIZING,
    )
    assert found == pytest.approx({"a": 0.5 / 1.5, "b": 1.0 / 1.5, "c": 0.0})
    assert sleeve_weights([sleeve("d", -1.0, 0.1)], SIZING) == {"d": 0.0}


def test_a_name_over_max_weight_shrinks_in_every_sleeve_alike():
    shares = combined(
        [sleeve("a", 1, 1, X=0.06, Y=0.01), sleeve("b", 1, 1, X=0.03)],
        {"a": 1.0, "b": 1.0},
        0.05,
    )
    assert shares["X"] == pytest.approx({"a": 0.05 * 2 / 3, "b": 0.05 / 3})
    assert shares["Y"] == {"a": 0.01}


def test_paper_and_real_fills_replay_into_separate_books():
    rows = [
        {
            "symbol": "X",
            "side": "buy",
            "quantity": 10,
            "strategy": "a",
            "dry_run": True,
        },
        {
            "symbol": "X",
            "side": "buy",
            "quantity": 4,
            "strategy": "a",
            "dry_run": False,
        },
        {
            "symbol": "X",
            "side": "sell",
            "quantity": 3,
            "strategy": "a",
            "dry_run": True,
        },
    ]
    assert replay(rows) == {
        (Account.PAPER, "a"): {"X": 7},
        (Account.LIVE, "a"): {"X": 4},
    }


def test_opening_shares_fill_buys_first_and_the_rest_is_sold():
    books = {
        (Account.LIVE, "opening"): {"X": 50.0, "Y": 8.0},
        (Account.LIVE, "b"): {"X": 5.0},
    }
    held = live_held(["a", "b"], books, {"a": {"X": 30}, "b": {"X": 10}})
    assert held == {"a": {"X": 30.0, "Y": 0.0}, "b": {"X": 25.0, "Y": 8.0}}
    quotes = {"X": Quote(price=10.0, adv=1e6, sector="tech")}
    done = diff("b", Account.LIVE, held["b"], {"X": 10}, quotes=quotes, bound=0.02)
    assert [(o.side, o.quantity) for o in done.orders] == [("sell", 15)]
    assert [(h.symbol, h.quantity) for h in done.unmanaged] == [("Y", 8.0)]


def test_unknown_adv_cuts_the_whole_order():
    quotes = {"X": Quote(price=10.0, adv=math.nan, sector="tech")}
    done = diff("a", Account.PAPER, {}, {"X": 10}, quotes=quotes, bound=0.02)
    assert done.orders == ()
    assert [(c.wanted, c.kept) for c in done.cuts] == [(10, 0)]
