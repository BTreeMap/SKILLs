"""Columnar rows a source yields and the fixed parquet schemas they become.

Dates travel as int64 days since 1970-01-01 and as `date32` on disk.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray

from btm_corekit import CommandError

Floats = NDArray[np.float64]
Days = NDArray[np.int64]
Texts = NDArray[np.str_]


class Source(StrEnum):
    CSV = "csv"
    FRENCH = "french"
    EDGAR = "edgar"
    TIINGO = "tiingo"


class Table(StrEnum):
    """`returns` is a run's own series, written by `measure`, never loaded."""

    BARS = "bars"
    EVENTS = "events"
    RETURNS = "returns"


BAR_PRICES = ("open", "high", "low", "close", "volume", "adj_factor")
BARS_SCHEMA = pa.schema(
    [("symbol", pa.string()), ("date", pa.date32())]
    + [(name, pa.float64()) for name in BAR_PRICES]
    + [("exchange", pa.string())]
)
EVENTS_SCHEMA = pa.schema(
    [
        ("symbol", pa.string()),
        ("field", pa.string()),
        ("event_time", pa.date32()),
        ("knowledge_time", pa.date32()),
        ("value", pa.float64()),
    ]
)
RETURNS_SCHEMA = pa.schema(
    [("date", pa.date32()), ("gross", pa.float64()), ("net", pa.float64())]
)
SCHEMAS = {
    Table.BARS: BARS_SCHEMA,
    Table.EVENTS: EVENTS_SCHEMA,
    Table.RETURNS: RETURNS_SCHEMA,
}


def day_of(value: date) -> int:
    return int(np.datetime64(value, "D").astype(np.int64))


def date_of(day: int) -> date:
    return date.fromisoformat(str(np.datetime64(day, "D")))


def days(values: Sequence[str], where: str) -> Days:
    """ISO dates to days, vectorized; a bad one is named by its 1-based row."""
    try:
        return np.array(values, dtype="datetime64[D]").astype(np.int64)
    except ValueError:
        for row, value in enumerate(values, start=1):
            try:
                np.datetime64(value, "D")
            except ValueError:
                raise CommandError(
                    f"{where} row {row}: {value!r} is no YYYY-MM-DD date"
                ) from None
        raise


def texts(values: Sequence[str]) -> Texts:
    return np.array(values, dtype=np.str_) if values else np.empty(0, dtype="<U1")


@dataclass(frozen=True, slots=True)
class Bars:
    """Daily bars, one row per (symbol, date); `exchange` empty when unknown."""

    symbol: Texts
    date: Days
    open: Floats
    high: Floats
    low: Floats
    close: Floats
    volume: Floats
    adj_factor: Floats
    exchange: Texts

    def __len__(self) -> int:
        return len(self.symbol)

    def keep(self, mask: NDArray[np.bool_]) -> Bars:
        return Bars.columns(
            {name: getattr(self, name)[mask] for name in self.__slots__}
        )

    @classmethod
    def columns(cls, arrays: Mapping[str, NDArray[Any]]) -> Bars:
        """From arrays named by field; `Bars.__slots__` lists the names."""
        return cls(**arrays)

    def arrow(self) -> pa.Table:
        columns = [pa.array(self.symbol, pa.string())]
        columns.append(pa.array(self.date.astype("datetime64[D]")))
        columns += [pa.array(getattr(self, name), pa.float64()) for name in BAR_PRICES]
        columns.append(pa.array(self.exchange, pa.string()))
        return pa.Table.from_arrays(columns, schema=BARS_SCHEMA)

    @classmethod
    def of(cls, table: pa.Table) -> Bars:
        prices = {name: floats_of(table, name) for name in BAR_PRICES}
        return cls.columns(
            {
                "symbol": texts_of(table, "symbol"),
                "date": days_of(table, "date"),
                "exchange": texts_of(table, "exchange"),
                **prices,
            }
        )


@dataclass(frozen=True, slots=True)
class EventRows:
    """Point-in-time rows: what `value` was for `event_time`, known on
    `knowledge_time`. A restatement is another row with a later one."""

    symbol: Texts
    field: Texts
    event_time: Days
    knowledge_time: Days
    value: Floats

    def __len__(self) -> int:
        return len(self.symbol)

    def keep(self, mask: NDArray[np.bool_]) -> EventRows:
        return EventRows.columns(
            {name: getattr(self, name)[mask] for name in self.__slots__}
        )

    @classmethod
    def columns(cls, arrays: Mapping[str, NDArray[Any]]) -> EventRows:
        return cls(**arrays)

    def arrow(self) -> pa.Table:
        return pa.Table.from_arrays(
            [
                pa.array(self.symbol, pa.string()),
                pa.array(self.field, pa.string()),
                pa.array(self.event_time.astype("datetime64[D]")),
                pa.array(self.knowledge_time.astype("datetime64[D]")),
                pa.array(self.value, pa.float64()),
            ],
            schema=EVENTS_SCHEMA,
        )

    @classmethod
    def of(cls, table: pa.Table) -> EventRows:
        return cls(
            texts_of(table, "symbol"),
            texts_of(table, "field"),
            days_of(table, "event_time"),
            days_of(table, "knowledge_time"),
            floats_of(table, "value"),
        )


def texts_of(table: pa.Table, name: str) -> Texts:
    return texts(table.column(name).to_pylist())


def days_of(table: pa.Table, name: str) -> Days:
    stamps: NDArray[np.datetime64] = table.column(name).to_numpy()
    return stamps.astype("datetime64[D]").astype(np.int64)


def floats_of(table: pa.Table, name: str) -> Floats:
    values: NDArray[Any] = table.column(name).to_numpy()
    return values.astype(np.float64)


def bars_from(
    symbol: Sequence[str],
    on: Sequence[str],
    prices: Mapping[str, Sequence[float]],
    exchange: Sequence[str],
    where: str,
) -> Bars:
    """Bars from parsed columns; a price column absent from `prices` is NaN,
    `adj_factor` absent is 1.0."""
    count = len(symbol)

    def column(name: str) -> Floats:
        if name in prices:
            return np.asarray(prices[name], dtype=np.float64)
        return np.full(count, 1.0 if name == "adj_factor" else np.nan)

    return Bars.columns(
        {
            "symbol": texts(symbol),
            "date": days(on, where),
            "exchange": texts(exchange),
            **{name: column(name) for name in BAR_PRICES},
        }
    )


@dataclass(frozen=True, slots=True)
class Loaded:
    """What one load yields; an empty table is not written."""

    bars: Bars | None
    events: EventRows | None

    def since(self, first: int) -> tuple[Loaded, int]:
        """Rows on or after day `first` (bars by date, events by knowledge
        time), and how many were dropped."""
        dropped = 0
        bars, events = self.bars, self.events
        if bars is not None:
            mask = bars.date >= first
            dropped += int((~mask).sum())
            bars = bars.keep(mask)
        if events is not None:
            mask = events.knowledge_time >= first
            dropped += int((~mask).sum())
            events = events.keep(mask)
        return Loaded(bars, events), dropped


def concat_bars(parts: Sequence[Bars]) -> Bars | None:
    if not parts:
        return None
    return Bars.columns(
        {
            name: np.concatenate([getattr(part, name) for part in parts])
            for name in Bars.__slots__
        }
    )


def concat_events(parts: Sequence[EventRows]) -> EventRows | None:
    if not parts:
        return None
    return EventRows.columns(
        {
            name: np.concatenate([getattr(part, name) for part in parts])
            for name in EventRows.__slots__
        }
    )
