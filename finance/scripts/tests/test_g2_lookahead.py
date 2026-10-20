"""G2: a strategy cannot see past its as-of day. Foresight computed outside
the API from future closes gets far above chance on the synthetic panel; the
same intent written against `Market` gets only the past and gets chance;
no `Market` accessor changes when everything after the day is poisoned."""

from __future__ import annotations

import numpy as np
import pytest
from btm_finance.api import Market
from btm_finance.data.assemble import build_events, build_panel, parse_universe
from btm_finance.data.panel import PANEL_ARRAYS, Events, Panel
from btm_finance.measuring import Peers, Setting, evaluate, rules_of
from btm_finance.models import (
    PREFERENCES_TEMPLATE,
    Limits,
    Preferences,
    StrategyConfig,
    limits_template,
)
from btm_finance.synthetic import make_panel

HORIZON = 63  # one quarter: the rebalance period of both strategies
NONE = Peers(trials=0, sharpes=(), series=())


def world(seed: int) -> tuple[Panel, Events]:
    data = make_panel(seed)
    events = build_events([(0, data.events)])
    return build_panel([(0, data.bars)], events, parse_universe(data.universe)), events


def setting(panel: Panel, events: Events) -> Setting:
    config = StrategyConfig(
        rebalance="quarterly", holding_days=HORIZON, long_only=False, family_id="g2"
    )
    limits = Limits.model_validate(limits_template(10_000_000))
    preferences = Preferences.model_validate(PREFERENCES_TEMPLATE)
    return Setting.of(panel, events, rules_of(limits, preferences, config))


def long_short(names: tuple[str, ...], key: np.ndarray) -> dict[str, float]:
    known = np.flatnonzero(np.isfinite(key))
    third = known.size // 3
    order = known[np.argsort(key[known], kind="stable")]
    weights = {names[i]: 1.0 for i in order[-third:].tolist()}
    return weights | {names[i]: -1.0 for i in order[:third].tolist()}


def foresight(panel: Panel):
    """Next quarter's closes, read from the full panel `measure` holds."""

    def pick(market: Market, params: object) -> dict[str, float]:
        row = int(np.searchsorted(panel.dates, market.day))
        later = min(row + 1 + HORIZON, len(panel.dates) - 1)
        columns = [panel.names.index(name) for name in market.names]
        ahead = panel.close[later, columns] / panel.close[row + 1, columns] - 1.0
        return long_short(market.names, ahead)

    return pick


def through_market(market: Market, params: object) -> dict[str, float]:
    """The same intent against the API: the newest `HORIZON + 1` closes are
    all it serves, and they end on the as-of day."""
    closes = market.close(HORIZON + 1)
    return long_short(market.names, closes[-1] / closes[0] - 1.0)


def test_foresight_outside_the_api_beats_chance_far():
    panel, events = world(1)
    card = evaluate(setting(panel, events), foresight(panel), {}, NONE).scorecard
    assert card.sharpe_net is not None
    assert card.sharpe_net > 3


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_same_intent_through_the_market_stays_at_chance(seed):
    panel, events = world(seed)
    card = evaluate(setting(panel, events), through_market, {}, NONE).scorecard
    assert card.sharpe_net is not None
    assert abs(card.sharpe_net) < 1
    assert card.dsr is not None
    assert card.dsr < 0.95


def poisoned(panel: Panel, events: Events, day: int) -> tuple[Panel, Events]:
    """Every bar after `day` and every event known after it set to 999."""
    later = panel.dates > day
    grids = {}
    for name in PANEL_ARRAYS:
        grid = getattr(panel, name).copy()
        grid[later] = 999.0
        grids[name] = grid
    bad = Panel(
        dates=panel.dates.copy(),
        names=panel.names,
        exchange=panel.exchange,
        sector=panel.sector,
        delisted=panel.delisted,
        **grids,
    )
    value = np.where(events.knowledge_time > day, 999.0, events.value)
    late = Events(
        events.name, events.field, events.event_time, events.knowledge_time, value
    )
    return bad, late


def accessors(market: Market) -> list[object]:
    return [
        market.day,
        market.names,
        market.sector,
        market.exchange,
        *(getattr(market, name)(300) for name in ("close", "open", "high", "low")),
        market.volume(300),
        market.adj(300),
        market.adv_dollar(21),
        market.fundamental("StockholdersEquity"),
        market.fundamental("CommonStockSharesOutstanding"),
        market.factor("mkt_rf", 300),
        market.factor("rf", 5),
    ]


def test_no_accessor_returns_anything_known_after_the_day():
    panel, events = world(4)
    for row in (40, 300, 700, 1100):
        day = int(panel.dates[row])
        honest = Market.at(panel, events, day)
        bad_panel, bad_events = poisoned(panel, events, day)
        probe = Market.at(bad_panel, bad_events, day)
        for left, right in zip(accessors(honest), accessors(probe), strict=True):
            if isinstance(left, np.ndarray):
                assert np.array_equal(left, right, equal_nan=True)
            else:
                assert left == right
        assert int(probe._bars.dates.max()) <= day
        assert int(probe._events.knowledge_time.max()) <= day
        assert not np.isin(999.0, probe._bars.close)


def test_a_lookback_is_a_positive_whole_count():
    panel, events = world(4)
    market = Market.at(panel, events, int(panel.dates[100]))
    for bad in (0, -1):
        with pytest.raises(ValueError, match="1 or more"):
            market.close(bad)
    with pytest.raises(TypeError):
        market.close(2.5)  # type: ignore[arg-type]
    assert market.close(500).shape == (500, len(market.names))
    assert np.isnan(market.close(500)[0]).all()  # padded before history starts
