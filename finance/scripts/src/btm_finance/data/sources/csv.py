"""Operator-supplied CSV exports: the universal route for any vendor's bars,
and for delisting and membership history as events."""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Self

import numpy as np
from pydantic import Field, model_validator

from btm_corekit import CommandError, Model, NonEmpty
from btm_finance.data.panel import DelistKind
from btm_finance.data.tables import (
    Bars,
    EventRows,
    Loaded,
    bars_from,
    days,
    texts,
)

BAR_REQUIRED = ("symbol", "date", "close")
BAR_OPTIONAL = ("open", "high", "low", "volume", "adj_factor", "exchange")
EVENT_REQUIRED = ("symbol", "field", "event_time", "knowledge_time", "value")
DELISTING = "delisting"


class CsvConfig(Model):
    """Paths absolute or relative to the working directory; `columns` maps a
    canonical column name to the header the export uses."""

    bars: NonEmpty | None = None
    events: NonEmpty | None = None
    columns: dict[str, NonEmpty] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _one_file(self) -> Self:
        if self.bars is None and self.events is None:
            raise ValueError("name a bars CSV, an events CSV, or both")
        return self


def records(
    data: bytes,
    columns: Mapping[str, str],
    wanted: tuple[str, ...],
    optional: tuple[str, ...],
    where: str,
) -> tuple[list[dict[str, str]], set[str]]:
    """Rows keyed by canonical name: `wanted` columns required, `optional` kept
    when present."""
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    headers = {name.strip().lower(): name for name in reader.fieldnames or []}

    def header(canonical: str) -> str | None:
        """The mapped header when this file has it, else the canonical one."""
        mapped = columns.get(canonical, canonical).strip().lower()
        return headers.get(mapped, headers.get(canonical))

    found = {
        canonical: name
        for canonical in (*wanted, *optional)
        if (name := header(canonical)) is not None
    }
    missing = [canonical for canonical in wanted if canonical not in found]
    if missing:
        raise CommandError(
            f"{where} lacks column(s) {', '.join(missing)}; "
            "map them under columns in the config"
        )
    rows = [
        {canonical: (row.get(name) or "").strip() for canonical, name in found.items()}
        for row in reader
    ]
    return rows, set(found)


def number(raw: str, where: str, line: int, *, required: bool) -> float:
    if not raw:
        if required:
            raise CommandError(f"{where} line {line}: a value is required")
        return math.nan
    try:
        return float(raw)
    except ValueError:
        raise CommandError(f"{where} line {line}: {raw!r} is no number") from None


def parse_bars(data: bytes, columns: Mapping[str, str], where: str) -> Bars:
    """Bars from CSV bytes: symbol, date, close required. A bar's knowledge
    time is its date."""
    rows, present = records(data, columns, BAR_REQUIRED, BAR_OPTIONAL, where)
    prices: dict[str, list[float]] = {}
    for name in ("open", "high", "low", "close", "volume", "adj_factor"):
        if name in present:
            prices[name] = [
                number(row[name], where, line, required=name == "close")
                for line, row in enumerate(rows, start=2)
            ]
    if "adj_factor" in prices:
        prices["adj_factor"] = [
            1.0 if math.isnan(v) else v for v in prices["adj_factor"]
        ]
    for line, row in enumerate(rows, start=2):
        if not row["symbol"]:
            raise CommandError(f"{where} line {line}: symbol is empty")
    return bars_from(
        [row["symbol"] for row in rows],
        [row["date"] for row in rows],
        prices,
        [row.get("exchange", "") for row in rows],
        where,
    )


def event_value(row: Mapping[str, str], where: str, line: int) -> float:
    """A `delisting` row may name its kind; any other value is a number."""
    raw = row["value"]
    if row["field"] == DELISTING:
        try:
            return DelistKind(raw.lower()).code
        except ValueError:
            pass
        value = number(raw, where, line, required=True)
        if value not in {kind.code for kind in DelistKind}:
            raise CommandError(
                f"{where} line {line}: a delisting value is performance (1) "
                "or merger (2)"
            )
        return value
    return number(raw, where, line, required=True)


def parse_events(data: bytes, columns: Mapping[str, str], where: str) -> EventRows:
    rows, _ = records(data, columns, EVENT_REQUIRED, (), where)
    for line, row in enumerate(rows, start=2):
        if not row["symbol"] or not row["field"]:
            raise CommandError(f"{where} line {line}: symbol and field are required")
    values = [event_value(row, where, line) for line, row in enumerate(rows, start=2)]
    return EventRows(
        texts([row["symbol"] for row in rows]),
        texts([row["field"] for row in rows]),
        days([row["event_time"] for row in rows], where),
        days([row["knowledge_time"] for row in rows], where),
        np.asarray(values, dtype=np.float64),
    )


def read(path: str) -> bytes:
    try:
        return Path(path).expanduser().read_bytes()
    except OSError as err:
        raise CommandError(f"cannot read {path}: {err}") from err


def fetch(config: CsvConfig) -> Loaded:
    bars = events = None
    if config.bars is not None:
        bars = parse_bars(read(config.bars), config.columns, config.bars)
    if config.events is not None:
        events = parse_events(read(config.events), config.columns, config.events)
    return Loaded(bars, events)
