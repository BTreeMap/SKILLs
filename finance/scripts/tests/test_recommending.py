"""The sizing law, the ruin bound, and the live book's pool, on hand-computed
numbers."""

from __future__ import annotations

import math

import numpy as np
import pytest
from btm_finance.models import KellyFractions, Sizing
from btm_finance.recommending import (
    Account,
    Candidate,
    Inputs,
    Proposal,
    Quote,
    RuinCut,
    Tier,
    combined,
    diff,
    edge_scale,
    live_held,
    propose,
    replay,
    sleeve_weights,
)

SIZING = Sizing(
    vol_target=0.10,
    kelly_fraction=KellyFractions(backtest=0.25, paper=0.50, live=0.75),
    max_weight=0.05,
)


def sleeve(  # noqa: PLR0913 - a candidate, every field named
    name: str,
    sharpe: float | None,
    vol: float | None,
    series: tuple[np.ndarray, np.ndarray] | None = None,
    *,
    dsr: float | None = 0.95,
    tier: Tier = Tier.BACKTEST,
    **weights: float,
):
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
        series=series,
        dsr=dsr,
        tier=tier,
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


@pytest.mark.parametrize(
    ("dsr", "scale"), [(0.5, 0.0), (0.8, 2 / 3), (0.95, 1.0), (0.3, 0.0), (None, 0.0)]
)
def test_edge_scale_rises_from_dsr_half_to_full_at_095(dsr, scale):
    assert edge_scale(dsr) == pytest.approx(scale)


def test_the_tier_and_edge_scale_set_the_kelly_cap():
    # Kelly 0.25 / 0.50 / 0.75 of Sharpe 0.2 over vol 0.2, times edge 2/3;
    # vol weight 0.5 never binds.
    found = sleeve_weights(
        [
            sleeve(t.value, 0.2, 0.2, dsr=0.8, tier=t)
            for t in (Tier.BACKTEST, Tier.PAPER, Tier.LIVE)
        ],
        SIZING,
    )
    assert found == pytest.approx(
        {"backtest": 0.25 * 2 / 3, "paper": 0.5 * 2 / 3, "live": 0.75 * 2 / 3}
    )


@pytest.mark.parametrize("sharpe", [None, -1.0, 0.0, 0.4, 5.0])
def test_a_probe_takes_exactly_the_probe_weight(sharpe):
    found = sleeve_weights(
        [sleeve("p", sharpe, 0.2, dsr=None, tier=Tier.PROBE)], SIZING
    )
    assert found == {"p": SIZING.probe_weight}


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


def planted(*candidates: Candidate, share: float = 0.5, sizing: Sizing = SIZING):
    quotes = {name: Quote(price=10.0, adv=1e9, sector="tech") for name in "XY"}
    return propose(
        Inputs(
            date="2020-01-31",
            as_of="2020-01-31",
            cap=1_000_000,
            sizing=sizing,
            bound=0.02,
            commission_bps=1.0,
            candidates=candidates,
            skipped=(),
            quotes=quotes,
            fills=(),
            previous=None,
            risk_share=share,
        )
    )


def test_a_copied_sleeve_halves_both_weights():
    # Both raw at min(0.1 / 0.2, 0.25 * 0.4 / 0.2) = 0.5; correlation 1, so
    # each divisor is 2 and each weight 0.25.
    rng = np.random.default_rng(3)
    days, net = np.arange(300, dtype=np.int64), rng.normal(0.0, 0.01, 300)
    found = planted(
        sleeve("a", 0.4, 0.2, (days, net), X=1.0),
        sleeve("b", 0.4, 0.2, (days, net.copy()), Y=1.0),
    )
    assert {n: s.divisor for n, s in found.sleeves.items()} == pytest.approx(
        {"a": 2.0, "b": 2.0}
    )
    assert {n: s.weight for n, s in found.sleeves.items()} == pytest.approx(
        {"a": 0.25, "b": 0.25}
    )
    assert found.effective_streams == pytest.approx(1.0)


def test_risk_share_is_reported_and_nothing_is_cut():
    # a: 0.5 at vol 0.20 is risk 0.10; b: 1.0 at vol 0.05 is risk 0.05; sum
    # 1.5 scales both by 2/3, shares stay 2/3 and 1/3; a is over 0.5.
    found = planted(sleeve("a", 0.4, 0.20, X=1.0), sleeve("b", 0.2, 0.05, Y=1.0))
    assert {n: s.weight for n, s in found.sleeves.items()} == pytest.approx(
        {"a": 0.5 / 1.5, "b": 1.0 / 1.5}
    )
    assert found.advisory.risk_share == pytest.approx({"a": 2 / 3, "b": 1 / 3})
    assert (found.advisory.bound, found.advisory.over) == (0.5, ("a",))
    assert found.cuts == ()
    assert found.ruin is None  # no stored series
    assert found.reasons == {"ruin": "no stored net series for a, b"}


BOLD = Sizing(
    vol_target=1.0,
    kelly_fraction=KellyFractions(backtest=1.0, paper=1.0, live=1.0),
    max_weight=1.0,
)


def book_of(daily: float, days: int = 600) -> Candidate:
    rng = np.random.default_rng(5)
    net = rng.normal(0.0005, daily, days)
    vol = float(np.std(net, ddof=1)) * math.sqrt(252)
    return sleeve("a", 2.0, vol, (np.arange(days, dtype=np.int64), net), X=1.0)


def test_a_high_vol_book_is_scaled_to_the_ruin_bound_reproducibly():
    # Daily 4% at weight 1 is about 63% annual: far past a 35% bound.
    found = planted(book_of(0.04), sizing=BOLD)
    (cut,) = found.cuts
    assert isinstance(cut, RuinCut)
    assert found.ruin is not None and found.ruin.loss > BOLD.ruin_bound
    assert cut.scale == pytest.approx(BOLD.ruin_bound / found.ruin.loss)
    assert found.sleeves["a"].weight == pytest.approx(cut.scale)
    assert (found.ruin.paths, found.ruin.horizon, found.ruin.block) == (1000, 252, 21)
    again = planted(book_of(0.04), sizing=BOLD)
    assert again.model_dump() == found.model_dump()


def test_a_quiet_book_takes_no_ruin_cut():
    found = planted(book_of(0.002), sizing=BOLD)
    assert found.ruin is not None and found.ruin.loss < BOLD.ruin_bound
    assert found.ruin.scale == 1.0
    assert found.cuts == ()
    assert found.sleeves["a"].weight == pytest.approx(1.0)


def test_under_252_common_periods_the_ruin_bound_is_null_with_reason():
    found = planted(book_of(0.04, days=200), sizing=BOLD)
    assert found.ruin is None
    assert found.reasons == {"ruin": "200 common periods, under 252"}


def test_a_proposal_written_before_tiers_and_ruin_reads_back():
    sleeve_row = {
        "strategy": "a",
        "account": "paper",
        "run_id": "a-run",
        "sharpe_net": 0.4,
        "vol_net": 0.2,
        "max_drawdown": 0.1,
        "vol_weight": 0.5,
        "kelly_cap": 0.5,
        "divisor": 1.0,
        "weight": 0.5,
        "code_changed": False,
        "unknown": 0,
        "signal": {},
    }
    summary = {
        "gross": 0.0,
        "net": 0.0,
        "cash": 1.0,
        "sectors": {},
        "top10": 0.0,
        "cost": 0.0,
        "turnover": 0.0,
        "orders": 0,
    }
    old = Proposal.model_validate(
        {
            "date": "2020-01-31",
            "as_of": "2020-01-31",
            "cap": 1_000_000,
            "sleeves": {"a": sleeve_row},
            "skipped": [],
            "targets": {},
            "orders": [],
            "summary": summary,
            "unmanaged": [],
            "carried": [],
            "cuts": [],
            "regime": None,
            "effective_streams": None,
        }
    )
    assert (old.sleeves["a"].tier, old.sleeves["a"].edge_scale) == (Tier.BACKTEST, 1.0)
    assert (old.ruin, old.reasons) == (None, {})
    assert (old.advisory.risk_share, old.advisory.bound, old.advisory.over) == (
        {},
        None,
        (),
    )
