#!/usr/bin/env python3
"""Operator's checker for this book: check one approval file against its
proposal, print the orders, record fills. Places no order: the operator
sends each one by hand at the broker.

Python 3 standard library only; imports nothing from btm_finance.

    bin/send approvals/<date>.json                 check, print order table
    bin/send approvals/<date>.json --dry-run       record dry-run fills at price
    bin/send approvals/<date>.json --fills <path>  record pasted fills, move to sent/

A fill table is CSV with header symbol,side,quantity,price,date (optional
strategy column), or a JSON list of objects with the same keys.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Written by `btm-finance start`: the command every fill is recorded through.
RECORD: tuple[str, ...] = ()
BOOK = Path(__file__).resolve().parent.parent
STRATEGY = re.compile(r"[a-z0-9][a-z0-9_-]*")
SIDES = ("buy", "sell")
FILL_KEYS = ("symbol", "side", "quantity", "price", "date")
Order = dict[str, Any]
Key = tuple[str, str, str]  # symbol, side, strategy


def halt(reason: str) -> NoReturn:
    print(f"refused: {reason}", file=sys.stderr)
    raise SystemExit(1)


def located(raw: str) -> Path:
    """The file resolves under this book's `approvals/`."""
    approvals = (BOOK / "approvals").resolve()
    path = Path(raw).resolve()
    if not path.is_relative_to(approvals) or not path.is_file():
        halt(f"{raw} is not a file under {approvals}: only approvals/ sends")
    return path


def read_object(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        halt(f"unreadable {path}: {err}")
    if not isinstance(document, dict):
        halt(f"{path} is not one JSON object")
    return document


def dated(document: dict[str, Any], today: str) -> list[Order]:
    """Written for today; an approval never carries over a day."""
    if document.get("date") != today:
        halt(
            f"approval dated {document.get('date')!r}, today is {today} (UTC): "
            "write a new approval today"
        )
    orders = document.get("orders")
    if not isinstance(orders, list) or not orders:
        halt('approval needs a non-empty "orders" list')
    if not all(isinstance(order, dict) for order in orders):
        halt("every order is one JSON object")
    return orders


def key_of(order: Order) -> Key:
    return (
        str(order.get("symbol")),
        str(order.get("side")),
        str(order.get("strategy")),
    )


def proposed(document: dict[str, Any]) -> frozenset[Key]:
    """The orders of the proposal the approval names, by symbol, side, strategy."""
    stem = document.get("proposal")
    folder = (BOOK / "proposals").resolve()
    if not isinstance(stem, str) or not stem:
        halt('approval needs "proposal": the proposal file stem it approves')
    path = (folder / f"{stem}.json").resolve()
    if path.parent != folder or not path.is_file():
        halt(f"proposal {stem!r} names no file under {folder}")
    orders = read_object(path).get("orders")
    if not isinstance(orders, list):
        halt(f"proposal {stem} holds no orders list")
    return frozenset(key_of(order) for order in orders if isinstance(order, dict))


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def status_of(strategy: str) -> str:
    path = BOOK / "strategies" / strategy / "status"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


def order_problems(
    order: Order, cap: float, allowed: tuple[str, ...], known: frozenset[Key]
) -> list[str]:
    """One order: shape, proposal match, ADV participation, strategy status."""
    found: list[str] = []
    if not isinstance(order.get("symbol"), str) or not order["symbol"].strip():
        found.append("symbol is missing")
    if order.get("side") not in SIDES:
        found.append(f"side must be one of {', '.join(SIDES)}")
    quantity = number(order.get("quantity"))
    if quantity is None or quantity <= 0:
        found.append("quantity must be a positive number")
    participation = number(order.get("adv_participation"))
    if participation is None:
        found.append("adv_participation is missing")
    elif participation > cap:
        found.append(f"adv_participation {participation} exceeds limit {cap}")
    strategy = order.get("strategy")
    if not isinstance(strategy, str) or not STRATEGY.fullmatch(strategy):
        found.append("strategy must name a directory under strategies/")
        return found
    if key_of(order) not in known:
        found.append(
            f"{order.get('symbol')} {order.get('side')} {strategy} is no order "
            "of the proposal"
        )
    status = status_of(strategy)
    if status not in allowed:
        found.append(
            f"strategy {strategy} is {status or 'without status'}, "
            f"not {'|'.join(allowed)}"
        )
    return found


def checked(orders: list[Order], known: frozenset[Key], dry_run: bool) -> None:
    """Every order inside the bounds; all problems at once."""
    limits = read_object(BOOK / "limits.json")
    cap = number(limits.get("max_adv_participation"))
    if cap is None:
        halt("limits.json has no numeric max_adv_participation")
    allowed = ("live", "paper") if dry_run else ("live",)
    problems = [
        f"orders[{index}]: {problem}"
        for index, order in enumerate(orders)
        for problem in order_problems(order, cap, allowed, known)
    ]
    if dry_run:
        problems += [
            f"orders[{index}]: price must be a positive number for a dry run"
            for index, order in enumerate(orders)
            if (number(order.get("price")) or 0) <= 0
        ]
    if problems:
        halt("; ".join(problems))


def table(orders: list[Order]) -> str:
    header = f"{'symbol':<10} {'side':<4} {'quantity':>12} {'price':>10} strategy"
    rows = [
        f"{order['symbol']:<10} {order['side']:<4} {order['quantity']:>12} "
        f"{order.get('price', 'market')!s:>10} {order['strategy']}"
        for order in orders
    ]
    return "\n".join([header, *rows])


def read_fills(path: Path) -> list[dict[str, Any]]:
    """A JSON list of objects, or CSV whose header names every fill key."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as err:
        halt(f"unreadable fill table {path}: {err}")
    if raw.lstrip().startswith("["):
        try:
            rows = json.loads(raw)
        except ValueError as err:
            halt(f"fill table {path} is not JSON: {err}")
        objects = [row for row in rows if isinstance(row, dict)]
        if len(objects) != len(rows):
            halt(f"fill table {path}: every entry is one JSON object")
        return objects
    reader = csv.DictReader(io.StringIO(raw))
    header = [name.strip() for name in reader.fieldnames or []]
    missing = [key for key in FILL_KEYS if key not in header]
    if missing:
        halt(f"fill table {path} header lacks {', '.join(missing)}")
    return [
        {(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader
    ]


def positive(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        found = float(value)
    except (TypeError, ValueError):
        return None
    return found if found > 0 else None


def fill_of(
    row: dict[str, Any], orders: list[Order], today: str
) -> tuple[Order | None, str | None]:
    """One pasted fill as a ledger fill, or why not."""
    symbol, side = str(row.get("symbol", "")), str(row.get("side", ""))
    quantity, price = positive(row.get("quantity")), positive(row.get("price"))
    if quantity is None or price is None:
        return None, "quantity and price must be positive numbers"
    try:
        when = date.fromisoformat(str(row.get("date"))).isoformat()
    except ValueError:
        return None, f"date {row.get('date')!r} is no YYYY-MM-DD date"
    if when > today:
        return None, f"date {when} is after today {today}"
    named = row.get("strategy") or None
    sleeves = sorted(
        {
            str(order["strategy"])
            for order in orders
            if order.get("symbol") == symbol
            and order.get("side") == side
            and named in (None, order.get("strategy"))
        }
    )
    if not sleeves:
        return None, f"{symbol} {side} names no order of the approval"
    if len(sleeves) > 1:
        return None, f"{symbol} {side} is in {', '.join(sleeves)}: add a strategy"
    fill = {"symbol": symbol, "side": side, "quantity": quantity, "price": price}
    return {**fill, "date": when, "strategy": sleeves[0], "dry_run": False}, None


def pasted(path: Path, orders: list[Order], today: str) -> list[Order]:
    """Every pasted fill naming an order; all problems at once."""
    rows = read_fills(path)
    if not rows:
        halt(f"fill table {path} holds no fill")
    made = [fill_of(row, orders, today) for row in rows]
    problems = [f"fills[{i}]: {why}" for i, (_, why) in enumerate(made) if why]
    if problems:
        halt("; ".join(problems))
    return [fill for fill, _ in made if fill is not None]


def record(fills: list[Order]) -> int:
    """Append fills through the book's one ledger writer."""
    batch = json.dumps({"fills": fills})
    done = subprocess.run(
        [*RECORD, "record", str(BOOK), "--batch:stdin"],
        input=batch,
        text=True,
        capture_output=True,
        check=False,
    )
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    if done.returncode != 0:
        print(f"fills not recorded; correct and rerun: {batch}", file=sys.stderr)
    return done.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("approval", help="approvals/<date>.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="record a dry-run fill at each order's price",
    )
    mode.add_argument(
        "--fills", type=Path, help="pasted fill table, CSV or JSON, to record"
    )
    parser.add_argument(
        "--today", type=date.fromisoformat, help="tests only: pin today's UTC date"
    )
    args = parser.parse_args(argv)
    # Operator's python3 may predate 3.11, where datetime.UTC first appears.
    now = datetime.now(timezone.utc).date()  # noqa: UP017 - see above
    today = (args.today or now).isoformat()
    path = located(args.approval)
    document = read_object(path)
    orders = dated(document, today)
    checked(orders, proposed(document), args.dry_run)
    print(table(orders))
    if not args.dry_run and args.fills is None:
        return 0
    if not RECORD:
        halt("RECORD is empty: scaffold bin/send with btm-finance start")
    if args.dry_run:
        # ponytail: fills at the approval's price field; a next-open fill from
        # loaded data is a later refinement.
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
            for order in orders
        ]
    else:
        fills = pasted(args.fills, orders, today)
    status = record([{**fill, "approval": path.name} for fill in fills])
    if status == 0 and args.fills is not None:
        sent = BOOK / "sent"
        sent.mkdir(exist_ok=True)
        shutil.move(path, sent / path.name)
    return status


if __name__ == "__main__":
    sys.exit(main())
