#!/usr/bin/env python3
"""Operator-only sender for this book: guard one approval file, confirm, submit.

Python 3 standard library only. Imports nothing from btm_finance and no broker
SDK: the broker adapter is `submit` below, and the operator writes it.

    bin/send approvals/<date>.json            real send, in a terminal
    bin/send approvals/<date>.json --dry-run  hypothetical fills; moves nothing
"""

from __future__ import annotations

import argparse
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
Order = dict[str, Any]


def halt(reason: str) -> NoReturn:
    print(f"refused: {reason}", file=sys.stderr)
    raise SystemExit(1)


def submit(orders: list[Order]) -> list[Order]:
    """Broker adapter: send each order, wait, return one fill per order with
    symbol, side, quantity, price, strategy. Fetch the key from the OS
    keychain behind its prompt; never store it in the book."""
    del orders
    print("no broker adapter installed: edit bin/send", file=sys.stderr)
    raise SystemExit(1)


def located(raw: str) -> Path:
    """Guard 1: the file resolves under this book's `approvals/`."""
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
    """Guard 2: written for today; an approval never carries over a day."""
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


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def order_problems(order: Order, cap: float, allowed: tuple[str, ...]) -> list[str]:
    """Guard 3 for one order: shape, ADV participation, strategy status."""
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
    status_file = BOOK / "strategies" / strategy / "status"
    status = (
        status_file.read_text(encoding="utf-8").strip() if status_file.is_file() else ""
    )
    if status not in allowed:
        found.append(
            f"strategy {strategy} is {status or 'without status'}, "
            f"not {'|'.join(allowed)}"
        )
    return found


def checked(orders: list[Order], dry_run: bool) -> None:
    """Guard 3: every order inside the hard bounds, all problems at once."""
    limits = read_object(BOOK / "limits.json")
    cap = number(limits.get("max_adv_participation"))
    if cap is None:
        halt("limits.json has no numeric max_adv_participation")
    allowed = ("live", "paper") if dry_run else ("live",)
    problems = [
        f"orders[{index}]: {problem}"
        for index, order in enumerate(orders)
        for problem in order_problems(order, cap, allowed)
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


def confirmed() -> None:
    """Guard 4: a person at a terminal types the literal word."""
    if not sys.stdin.isatty():
        halt("a real send needs a terminal: run bin/send yourself")
    try:
        typed = input("type yes to send these orders: ")
    except EOFError:
        halt("no confirmation; nothing sent")
    if typed != "yes":
        halt("not confirmed; nothing sent")


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
        print(f"fills not recorded; record them by hand: {batch}", file=sys.stderr)
    return done.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("approval", help="approvals/<date>.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fill at each order's price; send nothing",
    )
    parser.add_argument(
        "--today", type=date.fromisoformat, help="tests only: pin today's UTC date"
    )
    args = parser.parse_args(argv)
    # Operator's python3 may predate 3.11, where datetime.UTC first appears.
    now = datetime.now(timezone.utc).date()  # noqa: UP017 - see above
    today = (args.today or now).isoformat()
    path = located(args.approval)
    orders = dated(read_object(path), today)
    checked(orders, args.dry_run)
    print(table(orders))
    if not RECORD:
        halt("RECORD is empty: scaffold bin/send with btm-finance start")
    if args.dry_run:
        # ponytail: fills at the approval's price field; the ceiling is that
        # price, and a next-open fill from loaded data is a later refinement.
        fills = [
            {
                "symbol": order["symbol"],
                "side": order["side"],
                "quantity": order["quantity"],
                "price": order["price"],
                "strategy": order["strategy"],
            }
            for order in orders
        ]
    else:
        confirmed()
        fills = submit(orders)
    stamped = [
        {**fill, "date": today, "dry_run": args.dry_run, "approval": path.name}
        for fill in fills
    ]
    status = record(stamped)
    if status == 0 and not args.dry_run:
        sent = BOOK / "sent"
        sent.mkdir(exist_ok=True)
        shutil.move(path, sent / path.name)
    return status


if __name__ == "__main__":
    sys.exit(main())
