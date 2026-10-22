"""The data API: `Market`, which a strategy sees, and the book readers a
`tools/` or `lib/` script uses instead of touching ledger or parquet files.

`Market` is bound to one as-of day and one name set. Accessors count back
from that day by rows; none takes a date. Bars are cut at the day and events
at their knowledge time before a `Market` exists, so no attribute, private
or public, holds anything later.

Book readers, all read-only; append to the ledger only through `record`:

- `open_book(path)`: the `Book` at a path; refuses one without `book.json`.
- `ledger(book, kind)`: newest-wins rows of one kind (`hypothesis`,
  `critique`, `decision`, `fill`, `incident`, `regime`, `run`), superseded
  lines dropped; `run` joins every runs file, oldest first by `ts`.
- `research(book)`: research names' bars and events, built once;
  `.at(day)` is the `Market` on the last bar on or before `day`, `.dates`
  the bar dates. Held-out names never enter it. `.folds("train")` serves
  only the training blocks, for the miner delegate; `"test"` refuses.
- `receipt(text)`: a delegate's final message checked against `Receipt`.
- `outside_scope(book, commit, scope)`: paths `git diff main...<commit>`
  names outside the unit's write scope.
"""

from __future__ import annotations

import json
import operator
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray

from btm_corekit import CommandError, parse_model
from btm_finance import git
from btm_finance import ledger as lines
from btm_finance.data.assemble import assemble
from btm_finance.data.panel import Events, Panel
from btm_finance.data.tables import Days, Floats, date_of, day_of
from btm_finance.ledger import Kind, Row
from btm_finance.models import Receipt
from btm_finance.store import (
    Book,
    held_out_list,
    load_limits,
    open_book,
    read_bytes,
    run_files,
)

__all__ = [
    "FACTORS",
    "Book",
    "Market",
    "Receipt",
    "Research",
    "Training",
    "ledger",
    "on_dates",
    "open_book",
    "outside_scope",
    "receipt",
    "research",
]

FACTORS = "_factors"
Ints = NDArray[np.intp]


def rows_of(lookback: int) -> int:
    """A lookback is a whole count of rows, 1 or more; a float is refused."""
    count = operator.index(lookback)
    if count < 1:
        raise ValueError(f"lookback {count} must be 1 or more rows")
    return count


def carried_forward(values: Floats) -> Floats:
    """Each NaN cell takes the newest finite cell above it in its column; NaN
    above a column's first finite cell stays. O(T N)."""
    rows = np.arange(values.shape[0])[:, None]
    last = np.maximum.accumulate(np.where(np.isfinite(values), rows, -1), axis=0)
    out: Floats = np.where(
        last >= 0, values[np.maximum(last, 0), np.arange(values.shape[1])], np.nan
    )
    return out


@dataclass(frozen=True, slots=True)
class Market:
    """One as-of day of the names a strategy may see. `names` holds those with
    a close on the day; every array is rows by `names`, oldest row first, the
    last row the as-of day, NaN-padded on top when history is shorter.

    Build with `Market.at`; the panel and events must already hold only the
    names the strategy may see (research names, or held-out under --held-out).
    """

    _day: int
    _bars: Panel
    _events: Events
    _columns: Ints
    names: tuple[str, ...]
    sector: tuple[str, ...]
    exchange: tuple[str, ...]

    @classmethod
    def at(cls, panel: Panel, events: Events, day: int) -> Market:
        """O(log T + n + N): the cut is views; events are filtered once."""
        bars = panel.asof(day)
        last = bars.close[-1] if len(bars.dates) else np.full(len(bars.names), np.nan)
        columns: Ints = np.flatnonzero(np.isfinite(last))
        return cls(
            _day=day,
            _bars=bars,
            _events=events.asof(day),
            _columns=columns,
            names=tuple(bars.names[i] for i in columns),
            sector=tuple(bars.sector[i] for i in columns),
            exchange=tuple(bars.exchange[i].value for i in columns),
        )

    @property
    def day(self) -> int:
        """The as-of day, days since 1970-01-01."""
        return self._day

    def _window(self, grid: Floats, lookback: int) -> Floats:
        count = rows_of(lookback)
        rows = grid.shape[0]
        taken: Floats = grid[max(rows - count, 0) :, self._columns]
        if taken.shape[0] == count:
            return taken
        pad = np.full((count - taken.shape[0], len(self._columns)), np.nan)
        return np.vstack((pad, taken))

    def _scale(self, lookback: int) -> Floats:
        """`adj` over its value on the as-of day: ratios of later corporate
        actions only, so a vendor's back-adjusted level leaks nothing."""
        factor = self._window(self._bars.adj, lookback)
        today = np.nan_to_num(factor[-1], nan=1.0)
        return np.asarray(factor / today, dtype=np.float64)

    def close(self, lookback: int) -> Floats:
        """Total-return adjusted closes; the last row is the raw close. A row
        with no bar after a name's first bar is a day its exchange held no
        session (a universe spanning exchanges has them on each other's
        holidays): it carries the last close. Open, high, low, volume, and
        adj stay NaN there. O(T n) for n names served."""
        bars = self._bars
        price = bars.close[:, self._columns] * bars.adj[:, self._columns]
        count = rows_of(lookback)
        taken = carried_forward(price)[max(price.shape[0] - count, 0) :]
        if taken.shape[0] < count:
            pad = np.full((count - taken.shape[0], len(self._columns)), np.nan)
            taken = np.vstack((pad, taken))
        today = np.nan_to_num(self._window(bars.adj, 1)[-1], nan=1.0)
        return np.asarray(taken / today, dtype=np.float64)

    def open(self, lookback: int) -> Floats:
        return self._window(self._bars.open, lookback) * self._scale(lookback)

    def high(self, lookback: int) -> Floats:
        return self._window(self._bars.high, lookback) * self._scale(lookback)

    def low(self, lookback: int) -> Floats:
        return self._window(self._bars.low, lookback) * self._scale(lookback)

    def volume(self, lookback: int) -> Floats:
        """Shares traded, unadjusted."""
        return self._window(self._bars.volume, lookback)

    def adj(self, lookback: int) -> Floats:
        """Cumulative adjustment factor, 1.0 on the as-of day."""
        return self._scale(lookback)

    def adv_dollar(self, window: int) -> Floats:
        """Mean raw close times volume over the last `window` rows, per name;
        NaN rows skipped, NaN when none."""
        dollar = self._window(self._bars.close, window) * self.volume(window)
        present = np.isfinite(dollar)
        counts = present.sum(axis=0)
        sums = np.where(present, dollar, 0.0).sum(axis=0)
        mean: Floats = np.divide(
            sums, counts, out=np.full(len(self.names), np.nan), where=counts > 0
        )
        return mean

    def fundamental(self, field: str) -> Floats:
        """Newest value of `field` known on the day, per name; NaN where none.
        O(N log n)."""
        found = [self._events.latest(name, field, self._day) for name in self.names]
        return np.asarray(
            [np.nan if hit is None else hit[1] for hit in found], dtype=np.float64
        )

    def factor(self, field: str, lookback: int) -> Floats:
        """`_factors` field for the last `lookback` trading days, aligned with
        the price rows; NaN where absent or before history starts."""
        count = rows_of(lookback)
        dates = self._bars.dates[-count:]
        out = np.full(count, np.nan)
        out[count - len(dates) :] = on_dates(self._events, FACTORS, field, dates)
        return out


def on_dates(events: Events, name: str, field: str, dates: Days) -> Floats:
    """One (name, field) series on `dates` by event time, NaN where absent; the
    newest knowledge wins a date. O(n log n + D log n) for n rows of the pair."""
    rows = events.block(name, field)
    out = np.full(len(dates), np.nan)
    event_time = events.event_time[rows]
    if not len(event_time) or not len(dates):
        return out
    order = np.argsort(event_time, kind="stable")  # knowledge order kept
    stamps, values = event_time[order], events.value[rows][order]
    last = np.append(stamps[1:] != stamps[:-1], True)
    stamps, values = stamps[last], values[last]
    where = np.minimum(np.searchsorted(stamps, dates), len(stamps) - 1)
    hit = stamps[where] == dates
    out[hit] = values[where[hit]]
    return out


def ledger(book: Book, kind: str) -> list[Row]:
    """Newest-wins rows of one ledger kind; `run` joins every runs file,
    oldest first by `ts`. O(ledger bytes of that kind)."""
    try:
        chosen = Kind(kind)
    except ValueError:
        raise CommandError(
            f"no ledger kind {kind!r}: use one of {', '.join(Kind)}"
        ) from None
    if chosen is not Kind.RUN:
        return lines.current(lines.rows_of(read_bytes(book.path_of(chosen))))
    rows = [
        row
        for path in run_files(book)
        for row in lines.current(lines.rows_of(read_bytes(path)))
    ]
    return sorted(rows, key=lambda row: str(row.get("ts", "")))


def market_on(panel: Panel, events: Events, day: date) -> Market:
    """`Market` on the last bar on or before `day`. O(log T + N)."""
    row = panel.through(day_of(day)) - 1
    if row < 0:
        raise CommandError(f"no bar on or before {day}; load prices first")
    return Market.at(panel, events, int(panel.dates[row]))


@dataclass(frozen=True, slots=True)
class Training:
    """Bars and events cut at the last training date: the test block is
    absent, not hidden. Build with `research(book).folds("train")`."""

    _panel: Panel
    _events: Events

    @property
    def dates(self) -> tuple[date, ...]:
        """Training bar dates, oldest first."""
        return tuple(date_of(int(day)) for day in self._panel.dates)

    def at(self, day: date) -> Market:
        """`Market` on the last training bar on or before `day`; a day past
        the last training date or before the first refuses."""
        first, last = self._panel.dates[0], self._panel.dates[-1]
        if not first <= day_of(day) <= last:
            raise CommandError(
                f"{day} is outside training dates {date_of(int(first))} to "
                f"{date_of(int(last))}; the test block stays closed to research"
            )
        return market_on(self._panel, self._events, day)


TEST_CLOSED = (
    'folds("test") is refused: the miner rule reads training folds only; '
    "measure alone scores the test block"
)


@dataclass(frozen=True, slots=True)
class Research:
    """Research names' bars and events; build with `research(book)`."""

    _panel: Panel
    _events: Events
    _folds: int

    @property
    def dates(self) -> tuple[date, ...]:
        """Every bar date, oldest first."""
        return tuple(date_of(int(day)) for day in self._panel.dates)

    def at(self, day: date) -> Market:
        """`Market` on the last bar on or before `day`. O(log T + N)."""
        return market_on(self._panel, self._events, day)

    def folds(self, part: str) -> Training:
        """`"train"`: the first `folds - 1` of `thresholds.folds` equal
        contiguous blocks of bar dates; the last block is the test block."""
        if part == "test":
            raise CommandError(TEST_CLOSED)
        if part != "train":
            raise CommandError(f'no fold part {part!r}; use "train"')
        blocks = np.array_split(np.arange(len(self._panel.dates)), self._folds)
        start = int(blocks[-1][0]) if len(blocks[-1]) else 0
        if start == 0:
            raise CommandError(
                f"{len(self._panel.dates)} bar dates leave no training block "
                f"across {self._folds} folds; load more prices"
            )
        last = int(self._panel.dates[start - 1])
        return Training(self._panel.asof(last), self._events.asof(last))


def research(book: Book) -> Research:
    """Every stored file assembled, re-hashed on read, cut to research names.
    O(store bytes)."""
    panel, events = assemble(book)
    hidden = held_out_list(book)
    names = frozenset(name for name in panel.names if name not in hidden)
    folds = load_limits(book).thresholds.folds
    return Research(panel.only(names), events.only(names), folds)


def receipt(text: str) -> Receipt:
    """A delegate's final message decoded as one `Receipt`, or a
    `CommandError` naming every problem with its field path."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise CommandError(f"receipt is not one JSON object: {err}") from None
    if not isinstance(data, dict):
        raise CommandError(f"receipt is {type(data).__name__}, not a JSON object")
    return parse_model(Receipt, data, "receipt")


def outside_scope(
    book: Book, commit: str, scope: Sequence[str], base: str = "main"
) -> tuple[str, ...]:
    """Each book-relative path `git diff base...commit` names outside `scope`:
    an entry ending in `/` holds every path under it, any other entry only
    itself. Empty: the delegate wrote within bounds."""

    def inside(path: str) -> bool:
        return any(
            path.startswith(entry) if entry.endswith("/") else path == entry
            for entry in scope
        )

    return tuple(
        path for path in git.changed(book.root, base, commit) if not inside(path)
    )
