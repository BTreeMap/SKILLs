"""A universe spanning exchanges: the date grid is the union of their sessions,
so a name has NaN bars on the other exchange's holidays. Such an interior
hole is a day with no session: price carried, return 0, no trade."""

from __future__ import annotations

import numpy as np
from btm_finance.api import Market
from btm_finance.data.panel import Delisting, DelistKind, Events, Exchange, Panel
from btm_finance.measuring import Prepared, Rules, Track, costed
from btm_finance.models import Rebalance
from btm_finance.scaffold import template
from btm_finance.whitelist import load_signal

FIRST = 15_000  # days since 1970-01-01


def no_events() -> Events:
    return Events(
        np.array([], dtype="U1"),
        np.array([], dtype="U1"),
        np.array([], dtype=np.int64),
        np.array([], dtype=np.int64),
        np.array([], dtype=np.float64),
    )


def panel_of(
    close: np.ndarray,
    exchange: tuple[Exchange, ...],
    delisted: tuple[tuple[Delisting, ...], ...] | None = None,
) -> Panel:
    days, width = close.shape
    names = tuple(f"N{i:02d}" for i in range(width))
    return Panel(
        dates=np.arange(FIRST, FIRST + days, dtype=np.int64),
        names=names,
        exchange=exchange,
        sector=("tech",) * width,
        open=close.copy(),
        high=close * 1.01,
        low=close * 0.99,
        close=close.copy(),
        volume=np.where(np.isfinite(close), 1e6, np.nan),
        adj=np.ones_like(close),
        delisted=delisted or ((),) * width,
    )


def test_the_bar_after_a_hole_carries_the_move_since_the_last_close():
    close = np.array(
        [
            [10.0, 20.0],
            [11.0, 21.0],
            [12.0, 22.0],
            [np.nan, 23.0],  # A's exchange is shut; B's trades
            [15.0, 24.0],
            [16.0, 25.0],
        ]
    )
    prep = Prepared.of(panel_of(close, (Exchange.TSX, Exchange.NYSE)), no_events(), {})
    assert prep.close_cc[3, 0] == 0.0
    assert np.isclose(prep.close_cc[4, 0], 15.0 / 12.0 - 1.0)
    assert np.isclose(prep.overnight[4, 0], 15.0 / 12.0 - 1.0)
    assert np.isclose(prep.close_cc[3, 1], 23.0 / 22.0 - 1.0)


def test_the_baseline_picks_names_on_a_union_calendar():
    rng = np.random.default_rng(3)
    days, width = 320, 12
    close = 50.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (days, width)), axis=0))
    tsx, nyse = slice(0, width // 2), slice(width // 2, width)
    close[np.arange(7, days - 1, 61), tsx] = np.nan  # US-only sessions
    close[np.arange(29, days - 1, 53), nyse] = np.nan  # Canada-only sessions
    panel = panel_of(
        close, (Exchange.TSX,) * (width // 2) + (Exchange.NYSE,) * (width // 2)
    )
    signal = load_signal(template("signal.tmpl"), "signal.py", "calendar_baseline")
    market = Market.at(panel, no_events(), int(panel.dates[-1]))
    weights = signal(market, {"momentum_days": 252, "skip_days": 21, "vol_days": 252})
    assert weights
    assert np.isclose(sum(weights.values()), 1.0)
    shown = market.close(days)
    assert np.isfinite(shown).all()
    assert shown[7, 0] == shown[6, 0]  # the hole carries the last close
    assert np.isnan(market.volume(days)[7, 0])  # and nothing traded


def test_a_delisted_name_returns_its_terminal_return_then_nothing():
    close = np.array(
        [
            [10.0, 20.0],
            [np.nan, 21.0],  # a holiday before the delisting
            [12.0, 22.0],
            [13.0, 23.0],
            [np.nan, 24.0],  # delisted: no bar from here
            [np.nan, 25.0],
            [np.nan, 26.0],
        ]
    )
    record = Delisting(day=FIRST + 4, kind=DelistKind.PERFORMANCE, known=FIRST + 4)
    panel = panel_of(close, (Exchange.NYSE, Exchange.NYSE), ((record,), ()))
    prep = Prepared.of(panel, no_events(), {"nyse": -0.3, "merger": 0.0})
    assert np.isclose(prep.close_cc[2, 0], 12.0 / 10.0 - 1.0)
    assert prep.dead[0] == 4
    assert prep.close_cc[4, 0] == -0.3
    assert prep.overnight[4, 0] == -0.3
    assert (prep.close_cc[5:, 0] == 0.0).all()
    assert (prep.overnight[5:, 0] == 0.0).all()


def test_selling_a_name_with_zero_adv_costs_a_finite_amount():
    days = 30
    rng = np.random.default_rng(5)
    close = np.column_stack(
        (
            50.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, days))),
            np.full(days, 10.15),  # quoted flat, never traded
        )
    )
    panel = panel_of(close, (Exchange.NYSE, Exchange.NASDAQ))
    panel = Panel(
        dates=panel.dates,
        names=panel.names,
        exchange=panel.exchange,
        sector=panel.sector,
        open=panel.open,
        high=panel.close.copy(),
        low=panel.close.copy(),
        close=panel.close,
        volume=np.column_stack((np.full(days, 1e6), np.zeros(days))),
        adj=panel.adj,
        delisted=panel.delisted,
    )
    prep = Prepared.of(panel, no_events(), {})
    trades = np.zeros((5, 2))
    trades[0] = (0.5, 0.5)
    track = Track(first=25, gross=np.zeros(5), trades=trades, exposure=1.0, unknown=0)
    rules = Rules(
        rebalance=Rebalance.MONTHLY,
        holding_days=21,
        long_only=True,
        asset_cap=1e6,
        max_weight=0.5,
        price_floor=1.0,
        adv_multiple=1.0,
        commission_bps=1.0,
        impact_coefficient=0.1,
        delisting={},
        excluded_symbols=frozenset(),
        excluded_sectors=frozenset(),
        folds=5,
        touches=(),
    )
    assert np.isfinite(costed(track, prep, rules).net).all()
