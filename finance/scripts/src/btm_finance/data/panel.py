"""The in-memory data model: `Panel` of daily bars and `Events`, point in time.

Days are int64 days since 1970-01-01. Every as-of accessor returns only what
was known on or before its day; a bar's knowledge time is its own date.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

from btm_finance.data.tables import Days, Floats, Texts

PANEL_ARRAYS = ("open", "high", "low", "close", "volume", "adj")


class Exchange(StrEnum):
    NYSE = "nyse"
    AMEX = "amex"
    NASDAQ = "nasdaq"
    TSX = "tsx"
    OTHER = "other"


def exchange_of(raw: str) -> Exchange:
    """A listing venue's name, case and spaces ignored; anything else `other`."""
    try:
        return Exchange(raw.strip().lower())
    except ValueError:
        return Exchange.OTHER


class DelistKind(StrEnum):
    """`performance` takes the terminal return by exchange in `limits.json`."""

    PERFORMANCE = "performance"
    MERGER = "merger"

    @property
    def code(self) -> float:
        """The `value` a `delisting` event carries for this kind."""
        match self:
            case DelistKind.PERFORMANCE:
                return 1.0
            case DelistKind.MERGER:
                return 2.0


def delist_kind(code: float) -> DelistKind | None:
    return next((kind for kind in DelistKind if kind.code == code), None)


@dataclass(frozen=True, slots=True)
class Delisting:
    day: int
    kind: DelistKind
    known: int


def frozen(array: NDArray[np.generic]) -> None:
    array.setflags(write=False)


def ascending(values: Days) -> bool:
    return bool(np.all(values[1:] > values[:-1]))


@dataclass(frozen=True, slots=True)
class Panel:
    """Bars on a (dates, names) grid, NaN where absent; `adj` is the cumulative
    adjustment factor, 1.0 on a bar that carries none. `delisted[i]` holds
    name i's delisting records in knowledge order, newest last."""

    dates: Days
    names: tuple[str, ...]
    exchange: tuple[Exchange, ...]
    sector: tuple[str, ...]
    open: Floats
    high: Floats
    low: Floats
    close: Floats
    volume: Floats
    adj: Floats
    delisted: tuple[tuple[Delisting, ...], ...]

    def __post_init__(self) -> None:
        """O(T + N log N): grids are checked by dtype and shape only."""
        if self.dates.dtype != np.int64 or self.dates.ndim != 1:
            raise ValueError("dates must be one int64 axis")
        if not ascending(self.dates):
            raise ValueError("dates must ascend strictly")
        if list(self.names) != sorted(set(self.names)):
            raise ValueError("names must be unique and sorted")
        width = len(self.names)
        for per_name in (self.exchange, self.sector, self.delisted):
            if len(per_name) != width:
                raise ValueError("exchange, sector, delisted need one entry per name")
        shape = (len(self.dates), width)
        for name in PANEL_ARRAYS:
            grid: Floats = getattr(self, name)
            if grid.dtype != np.float64 or grid.shape != shape:
                raise ValueError(f"{name} must be float64 of shape {shape}")
        frozen(self.dates)
        for name in PANEL_ARRAYS:
            frozen(getattr(self, name))

    def through(self, day: int) -> int:
        """How many dates fall on or before `day`. O(log T)."""
        return int(np.searchsorted(self.dates, day, side="right"))

    def asof(self, day: int) -> Panel:
        """Rows dated on or before `day`, delisting records known by then.
        O(log T) to cut, views not copies; O(N log N + D) to check and filter."""
        cut = self.through(day)
        grids = {name: getattr(self, name)[:cut] for name in PANEL_ARRAYS}
        return Panel(
            dates=self.dates[:cut],
            names=self.names,
            exchange=self.exchange,
            sector=self.sector,
            delisted=tuple(
                tuple(record for record in records if record.known <= day)
                for records in self.delisted
            ),
            **grids,
        )

    def delisting(self, index: int) -> Delisting | None:
        """Name `index`'s newest delisting record, or None."""
        records = self.delisted[index]
        return records[-1] if records else None


def events_sorted(name: Texts, field: Texts, known: Days, event: Days) -> bool:
    """Adjacent rows ordered by (name, field, knowledge_time, event_time). O(n)."""
    if len(name) < 2:  # noqa: PLR2004 - order needs a pair
        return True
    a, b = slice(None, -1), slice(1, None)
    same_name = name[a] == name[b]
    same_field = same_name & (field[a] == field[b])
    same_known = same_field & (known[a] == known[b])
    ordered = (
        (name[a] < name[b])
        | (same_name & (field[a] < field[b]))
        | (same_field & (known[a] < known[b]))
        | (same_known & (event[a] <= event[b]))
    )
    return bool(np.all(ordered))


@dataclass(frozen=True, slots=True)
class Events:
    """Point-in-time table sorted by (name, field, knowledge_time, event_time)."""

    name: Texts
    field: Texts
    event_time: Days
    knowledge_time: Days
    value: Floats

    def __post_init__(self) -> None:
        arrays = [getattr(self, item.name) for item in fields(self)]
        if len({len(array) for array in arrays}) > 1:
            raise ValueError("event columns must share one length")
        for array, kind in zip(arrays, ("U", "U", "i", "i", "f"), strict=True):
            if array.dtype.kind != kind:
                raise ValueError(f"event column dtype {array.dtype} is not {kind}")
        if not events_sorted(
            self.name, self.field, self.knowledge_time, self.event_time
        ):
            raise ValueError("events must sort by name, field, knowledge_time")
        for array in arrays:
            frozen(array)

    def __len__(self) -> int:
        return len(self.name)

    def asof(self, day: int) -> Events:
        """Rows known on or before `day`, order kept. O(n)."""
        keep = self.knowledge_time <= day
        return Events(
            self.name[keep],
            self.field[keep],
            self.event_time[keep],
            self.knowledge_time[keep],
            self.value[keep],
        )

    def block(self, name: str, field: str) -> slice:
        """Rows of one (name, field), in knowledge order. O(log n)."""
        lo = int(np.searchsorted(self.name, name, side="left"))
        hi = int(np.searchsorted(self.name, name, side="right"))
        start = lo + int(np.searchsorted(self.field[lo:hi], field, side="left"))
        stop = lo + int(np.searchsorted(self.field[lo:hi], field, side="right"))
        return slice(start, stop)

    def latest(self, name: str, field: str, day: int) -> tuple[int, float] | None:
        """(event_time, value) of the newest row known on or before `day`;
        ties in knowledge time go to the latest event time. O(log n)."""
        rows = self.block(name, field)
        known = self.knowledge_time[rows]
        cut = int(np.searchsorted(known, day, side="right"))
        if cut == 0:
            return None
        row = rows.start + cut - 1
        return int(self.event_time[row]), float(self.value[row])
