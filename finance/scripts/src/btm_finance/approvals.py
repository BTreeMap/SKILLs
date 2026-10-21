"""The approval file the agent writes from the operator's reply, and the
pasted fill table, pure: the problems `check` names on an approval, and the
`fills` batch rows `record` builds from one. Callers read files; nothing
here touches the book."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from btm_corekit import CommandError, Diagnostic
from btm_finance.models import Side, Status
from btm_finance.recommending import account_of

Key = tuple[str, str, str]  # symbol, side, strategy
Row = dict[str, Any]
FILL_KEYS = ("symbol", "side", "quantity", "price", "date")
SLEEVES = frozenset({Status.PAPER, Status.PROBE, Status.LIVE})
SIDES = "|".join(Side)


def number(value: Any) -> float | None:
    """A JSON number or numeric text as float; bool, absent, or junk is None."""
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def key_of(order: Mapping[str, Any]) -> Key:
    return (
        str(order.get("symbol")),
        str(order.get("side")),
        str(order.get("strategy")),
    )


@dataclass(frozen=True, slots=True)
class Checked:
    """An approval read against its proposal: `orders` as the operator keys
    them, each with the `account` its strategy trades; `problems` empty
    when valid."""

    stem: str
    orders: tuple[Row, ...]
    problems: tuple[str, ...]


def status_of(raw: str | None) -> Status | None:
    try:
        return Status(raw or Status.RESEARCH.value)
    except ValueError:
        return None


def order_problems(
    order: Row, cap: float, statuses: Mapping[str, str], proposed: frozenset[Key]
) -> list[str]:
    """One order: shape, proposal match, ADV participation, strategy status."""
    found: list[str] = []
    if not isinstance(order.get("symbol"), str) or not order["symbol"].strip():
        found.append("symbol is missing")
    if order.get("side") not in tuple(Side):
        found.append(f"side must be one of {SIDES}")
    quantity = number(order.get("quantity"))
    if quantity is None or quantity <= 0:
        found.append("quantity must be a positive number")
    participation = number(order.get("adv_participation"))
    if participation is None:
        found.append("adv_participation is missing")
    elif participation > cap:
        found.append(f"adv_participation {participation} exceeds limit {cap}")
    strategy = str(order.get("strategy"))
    if key_of(order) not in proposed:
        found.append(
            f"{order.get('symbol')} {order.get('side')} {strategy} is no order "
            "of the proposal"
        )
    raw = statuses.get(strategy)
    if raw is None:
        found.append(f"strategy {strategy} names no directory under strategies/")
    elif status_of(raw) not in SLEEVES:
        found.append(
            f"strategy {strategy} is {raw or 'research'}, not paper|probe|live"
        )
    return found


def checked(  # noqa: PLR0913 - one approval against the book's live facts
    document: Any,
    stem: str,
    *,
    today: str,
    cap: float,
    statuses: Mapping[str, str],
    proposal_orders: Callable[[str], Sequence[Any] | None],
    witnessed: bool,
) -> Checked:
    """Every rule at once: `date` is today, `reply` quotes the operator, an
    `approve` decision hashed the file as it stands, `proposal` names a
    proposal, each order is one of it within the ADV bound on a sleeve.
    O(orders + proposal orders)."""
    if not isinstance(document, dict):
        return Checked(stem, (), ("approval is not one JSON object",))
    problems: list[str] = []
    if document.get("date") != today:
        problems.append(
            f"approval dated {document.get('date')!r}, today is {today} (UTC): "
            "write a new approval today"
        )
    reply = document.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        problems.append('approval needs "reply": the operator\'s words verbatim')
    if not witnessed:
        problems.append(
            f"no approve decision hashes approvals/{stem}.json as it stands: "
            "record one quoting the reply, with applied naming this file"
        )
    named = document.get("proposal")
    listed = proposal_orders(named) if isinstance(named, str) and named else None
    if listed is None:
        problems.append(f"proposal {named!r} names no file under proposals/")
    proposed = frozenset(key_of(o) for o in listed or () if isinstance(o, dict))
    raw = document.get("orders")
    orders = [o for o in raw if isinstance(o, dict)] if isinstance(raw, list) else []
    if not orders or len(orders) != len(raw or []):
        problems.append('approval needs a non-empty "orders" list of JSON objects')
    for index, order in enumerate(orders):
        problems += [
            f"orders[{index}]: {problem}"
            for problem in order_problems(order, cap, statuses, proposed)
        ]
    shown = tuple(order | {"account": account(order, statuses)} for order in orders)
    return Checked(stem, shown, tuple(problems))


def account(order: Row, statuses: Mapping[str, str]) -> str | None:
    """The position book the order's strategy trades: `paper` or `live`."""
    found = account_of(status_of(statuses.get(str(order.get("strategy")))))
    return None if found is None else found.value


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


def fill_of(
    row: Row, orders: Sequence[Row], statuses: Mapping[str, str], today: str
) -> Row | str:
    """One pasted fill as a `fills` batch row, or why not. The strategy comes
    from the row, else from the one approval order of that symbol and side."""
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
            return f"{symbol} {side} names no order of the approval"
        case [strategy]:
            pass
        case _:
            return f"{symbol} {side} is in {', '.join(sleeves)}: add a strategy column"
    if status_of(statuses.get(strategy)) is Status.PAPER:
        return f"strategy {strategy} is paper: record its fills with --dry-run"
    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "date": when.isoformat(),
        "strategy": strategy,
        "dry_run": False,
    }


def pasted(
    rows: Sequence[Row], orders: Sequence[Row], statuses: Mapping[str, str], today: str
) -> tuple[list[Row], list[Diagnostic]]:
    """Every pasted fill naming an order of the approval; all problems at once."""
    if not rows:
        return [], [Diagnostic("fills", "paste at least one fill into the table")]
    made = [fill_of(row, orders, statuses, today) for row in rows]
    return (
        [fill for fill in made if isinstance(fill, dict)],
        [
            Diagnostic(f"fills[{index}]", why)
            for index, why in enumerate(made)
            if isinstance(why, str)
        ],
    )


def dry_run(approval: Checked, today: str) -> tuple[list[Row], list[Diagnostic]]:
    """Paper orders as dry-run fills at the approval's price; any probe or
    live order, or any problem `check` names, refuses the whole file."""
    problems = [Diagnostic("approval", problem) for problem in approval.problems]
    problems += [
        Diagnostic(
            f"orders[{index}]",
            f"strategy {order.get('strategy')} trades the real account: send it "
            "by hand and record --fills:file",
        )
        for index, order in enumerate(approval.orders)
        if order.get("account") != "paper"
    ]
    problems += [
        Diagnostic(f"orders[{index}]", "price must be a positive number for a dry run")
        for index, order in enumerate(approval.orders)
        if (number(order.get("price")) or 0) <= 0
    ]
    fills = [
        {
            "symbol": order["symbol"],
            "side": order["side"],
            "quantity": order["quantity"],
            "price": order["price"],
            "date": today,
            "strategy": order["strategy"],
            "dry_run": True,
        }
        for order in approval.orders
    ]
    return ([], problems) if problems else (fills, [])
