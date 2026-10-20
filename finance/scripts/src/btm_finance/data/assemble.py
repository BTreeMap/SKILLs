"""The data model built from the raw store: every bar file unioned, the latest
load winning a (symbol, date); names from `<book>/universe.csv` when present.

Assembly is O(r log r) in stored rows r: one sort per table, then scatters.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from btm_corekit import CommandError
from btm_finance.data.panel import (
    PANEL_ARRAYS,
    Delisting,
    Events,
    Exchange,
    Panel,
    delist_kind,
    exchange_of,
)
from btm_finance.data.raw import read_manifest, read_store
from btm_finance.data.tables import Bars, EventRows, concat_bars, concat_events, texts
from btm_finance.store import Book

UNIVERSE = "universe.csv"
DELISTING = "delisting"
Index = NDArray[np.intp]


@dataclass(frozen=True, slots=True)
class Listing:
    sector: str
    exchange: str


def parse_universe(raw: str) -> dict[str, Listing]:
    """`symbol` required, `sector` and `exchange` optional; first row wins."""
    reader = csv.DictReader(io.StringIO(raw))
    fields = {name.strip().lower(): name for name in reader.fieldnames or []}
    if "symbol" not in fields:
        raise CommandError(f"{UNIVERSE} needs a symbol column")

    def cell(row: Mapping[str, str | None], name: str) -> str:
        return (row.get(fields[name]) or "").strip() if name in fields else ""

    found: dict[str, Listing] = {}
    for row in reader:
        symbol = cell(row, "symbol")
        if symbol:
            found.setdefault(
                symbol, Listing(cell(row, "sector"), cell(row, "exchange"))
            )
    return found


def ranks(parts: Sequence[tuple[int, Bars]] | Sequence[tuple[int, EventRows]]) -> Index:
    return np.concatenate(
        [np.full(len(rows), rank, dtype=np.intp) for rank, rows in parts]
    )


def last_of_groups(order: Index, *keys: NDArray[np.generic]) -> Index:
    """Of rows sorted by `order` with equal `keys` adjacent, the last of each
    run of equal keys."""
    if len(order) == 0:
        return order
    differs = np.zeros(len(order) - 1, dtype=bool)
    for key in keys:
        ordered = key[order]
        differs |= ordered[1:] != ordered[:-1]
    last: Index = order[np.append(differs, True)]
    return last


def build_events(parts: Sequence[tuple[int, EventRows]]) -> Events:
    """Union; on equal (symbol, field, event_time, knowledge_time) the latest
    load wins. O(r log r)."""
    rows = concat_events([part for _, part in parts])
    if rows is None:
        empty = np.empty(0, dtype=np.int64)
        return Events(texts([]), texts([]), empty, empty.copy(), np.empty(0))
    rank = ranks(parts)
    order = np.lexsort(
        (rank, rows.event_time, rows.knowledge_time, rows.field, rows.symbol)
    )
    keys = (rows.symbol, rows.field, rows.knowledge_time, rows.event_time)
    keep = last_of_groups(order, *keys)
    return Events(
        rows.symbol[keep],
        rows.field[keep],
        rows.event_time[keep],
        rows.knowledge_time[keep],
        rows.value[keep],
    )


def delistings(
    events: Events, names: Sequence[str]
) -> tuple[tuple[Delisting, ...], ...]:
    """Each name's `delisting` rows in knowledge order; value 1 is a
    performance delisting, 2 a merger."""
    per_name: dict[str, list[Delisting]] = {name: [] for name in names}
    for row in np.flatnonzero(events.field == DELISTING):
        symbol, code = str(events.name[row]), float(events.value[row])
        kind = delist_kind(code)
        if kind is None:
            raise CommandError(
                f"delisting for {symbol} holds {code}: performance is 1, merger 2"
            )
        if symbol in per_name:
            per_name[symbol].append(
                Delisting(
                    int(events.event_time[row]), kind, int(events.knowledge_time[row])
                )
            )
    return tuple(tuple(per_name[name]) for name in names)


def exchanges(
    bars: Bars,
    rank: Index,
    column: Index,
    universe: Mapping[str, Listing],
    names: Sequence[str],
) -> tuple[Exchange, ...]:
    """Universe first; else the latest load's non-empty bars column; else other."""
    stated = np.flatnonzero(bars.exchange != "")
    latest: dict[str, str] = {}
    if len(stated):
        order = stated[np.lexsort((rank[stated], column[stated]))]
        for row in last_of_groups(order, column):
            latest[names[column[row]]] = str(bars.exchange[row])

    def pick(name: str) -> Exchange:
        listing = universe.get(name)
        raw = listing.exchange if listing and listing.exchange else latest.get(name, "")
        return exchange_of(raw)

    return tuple(pick(name) for name in names)


def build_panel(
    parts: Sequence[tuple[int, Bars]], events: Events, universe: Mapping[str, Listing]
) -> Panel:
    """Union of bar files on one grid; the latest load wins a (symbol, date),
    the later row within one file. O(r log r + T*N)."""
    bars = concat_bars([part for _, part in parts])
    symbols = bars.symbol if bars is not None else texts([])
    names = tuple(sorted(set(universe) | {str(s) for s in np.unique(symbols)}))
    dates = (
        np.unique(bars.date) if bars is not None else np.empty(0, dtype=np.int64)
    ).astype(np.int64)
    shape = (len(dates), len(names))
    grids = {name: np.full(shape, np.nan) for name in PANEL_ARRAYS}
    exchange = tuple(
        exchange_of(universe[n].exchange) if n in universe else Exchange.OTHER
        for n in names
    )
    if bars is not None and len(bars):
        rank = ranks(parts)
        column = np.searchsorted(texts(list(names)), bars.symbol)
        row = np.searchsorted(dates, bars.date)
        cell = row * len(names) + column
        win = last_of_groups(np.lexsort((rank, cell)), cell)
        for name, values in zip(
            PANEL_ARRAYS,
            (bars.open, bars.high, bars.low, bars.close, bars.volume, bars.adj_factor),
            strict=True,
        ):
            grids[name][row[win], column[win]] = values[win]
        exchange = exchanges(bars, rank, column, universe, names)
    return Panel(
        dates=dates,
        names=names,
        exchange=exchange,
        sector=tuple(universe[n].sector if n in universe else "" for n in names),
        delisted=delistings(events, names),
        **grids,
    )


def assemble(book: Book) -> tuple[Panel, Events]:
    """Panel and Events from every stored file, each re-hashed on read."""
    stored = read_store(book, read_manifest(book))
    path = book.root / UNIVERSE
    universe = (
        parse_universe(path.read_text(encoding="utf-8")) if path.is_file() else {}
    )
    events = build_events(stored.events)
    return build_panel(stored.bars, events, universe), events
