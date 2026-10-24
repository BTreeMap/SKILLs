"""The data API: `Market`, which a strategy sees, and the book readers a
`tools/` or `lib/` script uses instead of touching ledger or parquet files.

`Market` is bound to one as-of day and one name set. Accessors count back
from that day by rows; none takes a date. Bars are cut at the day and events
at their knowledge time before a `Market` exists, so no attribute, private
or public, holds anything later.

Book readers, all read-only; append to the ledger only through `record`:

- `open_book(path)`: the `Book` at a path; refuses one without `book.json`.
- `ledger(book, kind)`: newest-wins rows of one kind (`hypothesis`,
  `critique`, `decision`, `fill`, `incident`, `run`), superseded lines
  dropped; `run` joins every runs file, oldest first by `ts`.
- `research(book)`: research names' bars and events, built once;
  `.at(day)` is the `Market` on the last bar on or before `day`, `.dates`
  the bar dates. Held-out names never enter it.
- `posts(book, channel=None, since=None)`: newest-wins channel posts from
  `load telegram`, ascending by channel and id; `since` a date cut on the
  post's UTC day.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray

from btm_corekit import CommandError
from btm_finance import ledger as lines
from btm_finance.data.assemble import assemble
from btm_finance.data.panel import Events, History, Panel
from btm_finance.data.posts import Post, current, of_channel
from btm_finance.data.raw import read_manifest, read_posts
from btm_finance.data.tables import Days, Floats, date_of, day_of
from btm_finance.ledger import Kind, Row
from btm_finance.store import Book, held_out_list, open_book, read_bytes, run_files

__all__ = [
    "FACTORS",
    "Book",
    "History",
    "Market",
    "Post",
    "Research",
    "ledger",
    "on_dates",
    "open_book",
    "posts",
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
    """One as-of day of the names a strategy may see. `names`: tuple of
    symbols in column order, those with a close on the day, inside a
    membership stretch when the name has any (`member_<index>` events: from
    entry `knowledge_time` to exit `event_time`; a name with none follows
    `universe.csv`). `sector`, `exchange`: tuples aligned to `names`. Rows
    are the union of every exchange's sessions. Every 2-D array is rows by
    `names`, oldest row first, the last row the as-of day, NaN-padded on top
    when history is shorter. Every accessor counts rows back; none takes a
    date. `measure` returns 0 on a name's non-session day, carries the whole
    move to its next bar, and fills a rebalance landing there at the carried
    close; a held name past exit returns 0 once its bars end.

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
        """O(log T + n + N + S): the cut is views; events are filtered once."""
        bars = panel.asof(day)
        last = bars.close[-1] if len(bars.dates) else np.full(len(bars.names), np.nan)
        columns: Ints = np.flatnonzero(np.isfinite(last) & panel.served(day))
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
        """Opens, adjusted as `close`; NaN on a non-session day."""
        return self._window(self._bars.open, lookback) * self._scale(lookback)

    def high(self, lookback: int) -> Floats:
        """Highs, adjusted as `close`; NaN on a non-session day."""
        return self._window(self._bars.high, lookback) * self._scale(lookback)

    def low(self, lookback: int) -> Floats:
        """Lows, adjusted as `close`; NaN on a non-session day."""
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

    def events(self, field: str, count: int) -> History:
        """Newest `count` events of `field` known on the day, per name: `value`,
        `event_time`, `knowledge_time`, each `count` rows by `names`, newest row
        last, NaN-padded on top; times are days since 1970-01-01. O(N count)
        after one O(n) pass per field."""
        return self._events.history(self.names, field, rows_of(count))

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
class Research:
    """Research names' bars and events; build with `research(book)`."""

    _panel: Panel
    _events: Events

    @property
    def dates(self) -> tuple[date, ...]:
        """Every bar date, oldest first."""
        return tuple(date_of(int(day)) for day in self._panel.dates)

    def at(self, day: date) -> Market:
        """`Market` on the last bar on or before `day`. O(log T + N)."""
        return market_on(self._panel, self._events, day)


def research(book: Book) -> Research:
    """Every stored file assembled, re-hashed on read, cut to research names.
    O(store bytes)."""
    panel, events = assemble(book)
    hidden = held_out_list(book)
    names = frozenset(name for name in panel.names if name not in hidden)
    return Research(panel.only(names), events.only(names))


def posts(
    book: Book, channel: str | None = None, since: date | None = None
) -> list[Post]:
    """Every stored post, re-hashed on read, newest load winning a repeated
    `(channel, id)`; `channel` matches without case. O(posts bytes)."""
    rows = current(read_posts(book, read_manifest(book)))
    if channel is not None:
        rows = of_channel(rows, channel)
    return [post for post in rows if since is None or post.day >= since]
