"""The pasted fill table, pure: the `fills` batch rows `record --fills:file
<table> --proposal <stem>` builds from one, against the proposal's orders.
Callers read files; nothing here touches the book."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from btm_corekit import CommandError, Diagnostic

Row = dict[str, Any]
FILL_KEYS = ("symbol", "side", "quantity", "price", "date")


def number(value: Any) -> float | None:
    """A JSON number or numeric text as float; bool, absent, or junk is None."""
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def table_rows(raw: str, name: str) -> list[Row]:
    """A JSON list of objects, or CSV whose header names every fill key."""
    if raw.lstrip().startswith("["):
        try:
            rows = json.loads(raw)
        except ValueError as err:
            raise CommandError(f"fill table {name} is not JSON: {err}") from err
        objects = [row for row in rows if isinstance(row, dict)]
        if len(objects) != len(rows):
            raise CommandError(f"fill table {name}: every entry is one JSON object")
        return objects
    reader = csv.DictReader(io.StringIO(raw))
    header = [field.strip() for field in reader.fieldnames or []]
    missing = [key for key in FILL_KEYS if key not in header]
    if missing:
        raise CommandError(f"fill table {name} header lacks {', '.join(missing)}")
    return [
        {(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader
    ]


def fill_date(raw: Any, today: str) -> date | str:
    """The fill's date, or why not: no date, or after today."""
    try:
        when = date.fromisoformat(str(raw))
    except ValueError:
        return f"date {raw!r} is no YYYY-MM-DD date"
    return f"date {when} is after today {today}" if when.isoformat() > today else when


def fill_of(row: Row, orders: Sequence[Mapping[str, Any]], today: str) -> Row | str:
    """One pasted fill as a `fills` batch row, or why not. The strategy comes
    from the row, else from the one proposal order of that symbol and side."""
    symbol, side = str(row.get("symbol", "")), str(row.get("side", ""))
    quantity, price = number(row.get("quantity")), number(row.get("price"))
    if quantity is None or price is None or quantity <= 0 or price <= 0:
        return "quantity and price must be positive numbers"
    when = fill_date(row.get("date"), today)
    if isinstance(when, str):
        return when
    named = row.get("strategy") or None
    sleeves = sorted(
        {
            str(order.get("strategy"))
            for order in orders
            if order.get("symbol") == symbol
            and order.get("side") == side
            and named in (None, order.get("strategy"))
        }
    )
    match sleeves:
        case []:
            return f"{symbol} {side} names no order of the proposal"
        case [strategy]:
            pass
        case _:
            return f"{symbol} {side} is in {', '.join(sleeves)}: add a strategy column"
    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "date": when.isoformat(),
        "strategy": strategy,
    }


def pasted(
    rows: Sequence[Row], orders: Sequence[Mapping[str, Any]], today: str
) -> tuple[list[Row], list[Diagnostic]]:
    """Every pasted fill naming an order of the proposal; all problems at once."""
    if not rows:
        return [], [Diagnostic("fills", "paste at least one fill into the table")]
    made = [fill_of(row, orders, today) for row in rows]
    return (
        [fill for fill in made if isinstance(fill, dict)],
        [
            Diagnostic(f"fills[{index}]", why)
            for index, why in enumerate(made)
            if isinstance(why, str)
        ],
    )
