"""The data API a strategy sees: `Market`, bound to one as-of day and one name
set. Accessors count back from that day by rows; none takes a date.

Bars are cut at the day and events at their knowledge time before a `Market`
exists, so no attribute, private or public, holds anything later.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from btm_finance.data.panel import Events, Panel
from btm_finance.data.tables import Days, Floats

FACTORS = "_factors"
Ints = NDArray[np.intp]


def rows_of(lookback: int) -> int:
    """A lookback is a whole count of rows, 1 or more; a float is refused."""
    count = operator.index(lookback)
    if count < 1:
        raise ValueError(f"lookback {count} must be 1 or more rows")
    return count


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
        """Total-return adjusted closes; the last row is the raw close."""
        return self._window(self._bars.close, lookback) * self._scale(lookback)

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
