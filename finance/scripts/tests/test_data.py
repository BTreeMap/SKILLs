"""The data model's laws: as-of never reaches past its day, the latest load
wins a duplicate, and the snapshot digest moves only with file bytes."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest
from btm_finance.api import Market, research
from btm_finance.data.assemble import build_events, build_panel, parse_universe
from btm_finance.data.panel import DelistKind, Events, Exchange
from btm_finance.data.raw import (
    Entry,
    Manifest,
    data_snapshot,
    default_since,
    stem_for,
)
from btm_finance.data.tables import (
    EventRows,
    Source,
    Table,
    bars_from,
    day_of,
    texts,
)
from btm_finance.store import open_book

from btm_corekit import CommandError

D = day_of(date(2024, 1, 2))


def events(rows: list[tuple[str, str, int, int, float]]) -> EventRows:
    return EventRows(
        texts([r[0] for r in rows]),
        texts([r[1] for r in rows]),
        np.asarray([r[2] for r in rows], dtype=np.int64),
        np.asarray([r[3] for r in rows], dtype=np.int64),
        np.asarray([r[4] for r in rows], dtype=np.float64),
    )


def random_events(seed: int, count: int = 400) -> Events:
    rng = np.random.default_rng(seed)
    event = rng.integers(0, 200, count)
    rows = [
        (
            f"N{rng.integers(0, 5)}",
            ("revenue", "assets")[rng.integers(0, 2)],
            int(event[i]),
            int(event[i] + rng.integers(0, 90)),
            float(rng.normal()),
        )
        for i in range(count)
    ]
    return build_events([(0, events(rows))])


@pytest.mark.parametrize("seed", range(5))
def test_asof_never_returns_a_later_knowledge_time(seed):
    table = random_events(seed)
    for day in range(-1, 300, 7):
        seen = table.asof(day)
        assert np.all(seen.knowledge_time <= day)
        assert len(seen) == int(np.sum(table.knowledge_time <= day))
        for name in ("N0", "N3"):
            got = table.latest(name, "revenue", day)
            mask = (
                (table.name == name)
                & (table.field == "revenue")
                & (table.knowledge_time <= day)
            )
            if not mask.any():
                assert got is None
                continue
            known = table.knowledge_time[mask]
            newest = known == known.max()
            expected_event = int(table.event_time[mask][newest].max())
            assert got is not None
            assert got[0] == expected_event
            assert table.knowledge_time[table.event_time == got[0]].min() <= day


def test_a_restatement_is_seen_only_from_its_knowledge_day():
    table = build_events(
        [
            (
                0,
                events(
                    [
                        ("A", "revenue", D, D + 30, 10.0),
                        ("A", "revenue", D, D + 90, 12.0),
                    ]
                ),
            )
        ]
    )
    assert table.latest("A", "revenue", D + 29) is None
    assert table.latest("A", "revenue", D + 30) == (D, 10.0)
    assert table.latest("A", "revenue", D + 89) == (D, 10.0)
    assert table.latest("A", "revenue", D + 90) == (D, 12.0)


def test_latest_load_wins_a_duplicate_event_and_bar():
    first = events([("A", "dividend", D, D, 0.5)])
    second = events([("A", "dividend", D, D, 0.6)])
    table = build_events([(1, second), (0, first)])
    assert table.value.tolist() == [0.6]

    old = bars_from(
        ["A", "A"], ["2024-01-02", "2024-01-03"], {"close": [1, 2]}, ["", ""], "old"
    )
    new = bars_from(["A"], ["2024-01-03"], {"close": [5]}, ["nasdaq"], "new")
    panel = build_panel([(1, new), (0, old)], table, {})
    assert panel.close[:, 0].tolist() == [1.0, 5.0]
    assert panel.exchange == (Exchange.NASDAQ,)
    assert panel.adj[:, 0].tolist() == [1.0, 1.0]


def test_panel_asof_cuts_dates_and_hides_a_later_delisting():
    bars = bars_from(
        ["A", "A", "B"],
        ["2024-01-02", "2024-01-05", "2024-01-03"],
        {"close": [1, 2, 3]},
        ["", "", ""],
        "bars",
    )
    code = DelistKind.MERGER.code
    table = build_events([(0, events([("B", "delisting", D + 5, D + 6, code)]))])
    universe = parse_universe("symbol,sector,exchange\nB,energy,NYSE\nC,,\n")
    panel = build_panel([(0, bars)], table, universe)
    assert panel.names == ("A", "B", "C")
    assert panel.sector == ("", "energy", "")
    assert panel.exchange == (Exchange.OTHER, Exchange.NYSE, Exchange.OTHER)
    assert np.isnan(panel.close[0, 1])
    assert panel.delisting(1) is not None
    assert panel.delisting(1).kind is DelistKind.MERGER
    early = panel.asof(D + 1)
    assert early.dates.tolist() == [D, D + 1]
    assert early.delisting(1) is None
    assert panel.asof(D + 6).delisting(1) is not None


def test_panel_refuses_unsorted_dates_and_frozen_grids():
    bars = bars_from(["A"], ["2024-01-02"], {"close": [1]}, [""], "b")
    panel = build_panel([(0, bars)], build_events([]), {})
    with pytest.raises(ValueError, match="read-only"):
        panel.close[0, 0] = 9.0
    with pytest.raises(ValueError, match="ascend"):
        type(panel)(
            **{
                **{f: getattr(panel, f) for f in panel.__slots__},
                "dates": np.array([2, 1], dtype=np.int64),
                "close": np.zeros((2, 1)),
            }
        )


def entry(sha: str, source: Source = Source.CSV, through: str = "2024-01-05") -> Entry:
    return Entry(
        path=f"data/raw/{source.value}/{sha[:4]}.bars.parquet",
        sha256=sha,
        rows=1,
        source=source,
        table=Table.BARS,
        loaded_at="2024-01-06T00:00:00+00:00",
        since=date(2024, 1, 1),
        through=date.fromisoformat(through),
    )


def test_data_snapshot_ignores_order_and_follows_bytes():
    a, b = entry("a" * 64), entry("b" * 64)
    assert data_snapshot(Manifest(files=(a, b))) == data_snapshot(
        Manifest(files=(b, a))
    )
    assert data_snapshot(Manifest(files=(a,))) != data_snapshot(Manifest(files=(b,)))


def test_default_since_follows_the_source_and_reaches_back_25_years():
    manifest = Manifest(files=(entry("a" * 64, through="2024-03-01"),))
    today = date(2024, 2, 29)
    assert default_since(manifest, Source.CSV, today) == date(2024, 3, 2)
    assert default_since(manifest, Source.TIINGO, today) == date(1999, 2, 28)


def test_stem_for_never_reuses_a_stored_name():
    assert stem_for([], date(2024, 1, 2)) == "2024-01-02"
    assert stem_for(["2024-01-02", "2024-01-02-2"], date(2024, 1, 2)) == "2024-01-02-3"


def test_history_holds_dates_newest_last_padded_and_as_of():
    rows = [
        ("A", "f", D, D + 2, 1.0),
        ("A", "f", D + 10, D + 12, 2.0),
        ("A", "f", D + 20, D + 40, 3.0),  # known after the as-of day
        ("B", "f", D + 5, D + 6, 9.0),
        ("B", "g", D + 5, D + 6, 7.0),
    ]
    seen = build_events([(0, events(rows))]).asof(D + 25)
    found = seen.history(("A", "B", "C"), "f", 3)
    nan = float("nan")
    assert np.array_equal(
        found.value, [[nan, nan, nan], [1.0, nan, nan], [2.0, 9.0, nan]], equal_nan=True
    )
    assert np.array_equal(found.event_time[1:, 0], [D, D + 10])
    assert np.array_equal(found.knowledge_time[1:, 0], [D + 2, D + 12])
    assert np.isnan(found.event_time[:, 2]).all()
    assert seen.history(("A",), "f", 1).value.tolist() == [[2.0]]
    assert np.isnan(seen.history(("A",), "absent", 2).value).all()


def test_market_events_reads_filings_by_knowledge_time(synthetic):
    book = open_book(str(synthetic(seed=7)))
    data = research(book)
    market = data.at(data.dates[400])
    found = market.events("StockholdersEquity", 4)
    assert found.value.shape == (4, len(market.names))
    known = found.knowledge_time[np.isfinite(found.knowledge_time)]
    assert known.size and (known <= market.day).all()
    lag = found.knowledge_time - found.event_time
    assert set(lag[np.isfinite(lag)].tolist()) == {40.0}
    newest = market.fundamental("StockholdersEquity")
    assert np.array_equal(found.value[-1], newest, equal_nan=True)


def served(panel, table, day):
    return Market.at(panel, table, day).names


def test_membership_serves_a_name_between_entry_knowledge_and_exit():
    names = ["A", "B", "C", "E"]
    stamps = [f"2024-01-{d:02d}" for d in range(2, 12)]
    bars = bars_from(
        [n for n in names for _ in stamps],
        stamps * len(names),
        {"close": [1.0] * len(names) * len(stamps)},
        [""] * len(names) * len(stamps),
        "bars",
    )
    rows = [
        ("A", "member_x", D + 3, D + 1, 1.0),  # announced D + 1
        ("A", "member_x", D + 5, D + 2, 0.0),  # leaves D + 5
        ("C", "member_x", D + 2, D + 2, 0.0),  # member before history
        ("E", "member_x", D + 3, D + 6, 0.0),  # exit known late
    ]
    table = build_events([(0, events(rows))])
    panel = build_panel([(0, bars)], table, {})
    assert served(panel, table, D) == ("B", "C", "E")
    assert served(panel, table, D + 1) == ("A", "B", "C", "E")
    assert served(panel, table, D + 2) == ("A", "B", "E")
    assert served(panel, table, D + 4) == ("A", "B", "E")
    assert served(panel, table, D + 5) == ("B", "E")
    assert served(panel, table, D + 6) == ("B",)
    bare = build_panel([(0, bars)], build_events([]), {})
    assert bare.members == ()
    assert served(bare, build_events([]), D + 6) == tuple(names)


def test_a_membership_value_other_than_entry_or_exit_is_refused():
    table = build_events([(0, events([("A", "member_x", D, D, 2.0)]))])
    bars = bars_from(["A"], ["2024-01-02"], {"close": [1]}, [""], "b")
    with pytest.raises(CommandError, match="entry is 1, exit 0"):
        build_panel([(0, bars)], table, {})
