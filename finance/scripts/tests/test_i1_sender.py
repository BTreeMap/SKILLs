"""Invariant 1: the book places no order. `bin/send` is stdlib only, checks
and prints; a dry run records fills at price; a pasted fill table naming an
approval order is recorded and the approval moves to `sent/`."""

from __future__ import annotations

import ast
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

TODAY = datetime.now(UTC).date().isoformat()


def set_status(book: Path, word: str) -> None:
    (book / "strategies" / "baseline" / "status").write_text(word + "\n")


def fill_lines(book: Path) -> list[dict]:
    path = book / "ledger" / "fills.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def test_the_sender_imports_only_the_standard_library(book):
    text = (book / "bin" / "send").read_text()
    tree = ast.parse(text)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}
    assert os.access(book / "bin" / "send", os.X_OK)
    assert "def submit" not in text


def test_a_plain_run_checks_and_prints_and_records_nothing(book, approve, send):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    done = send(str(file))
    assert done.returncode == 0, done.stderr
    assert "ABC" in done.stdout and "baseline" in done.stdout
    assert fill_lines(book) == []
    assert file.exists()


def test_dry_run_records_fills_at_price_and_moves_nothing(book, approve, send):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "paper")
    dry = send(str(file), "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert [(f["symbol"], f["price"], f["dry_run"]) for f in fill_lines(book)] == [
        ("ABC", 12.5, True)
    ]
    assert file.exists()
    assert not any((book / "sent").iterdir())


def test_a_pasted_fill_naming_an_order_is_recorded_and_the_file_sent(
    book, approve, send, tmp_path
):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    table = tmp_path / "fills.csv"
    table.write_text(f"symbol,side,quantity,price,date\nABC,buy,10,12.4,{TODAY}\n")
    done = send(str(file), "--fills", str(table))
    assert done.returncode == 0, done.stderr
    (fill,) = fill_lines(book)
    assert (fill["symbol"], fill["quantity"], fill["price"]) == ("ABC", 10, 12.4)
    assert (fill["strategy"], fill["dry_run"]) == ("baseline", False)
    assert fill["approval"] == file.name
    assert not file.exists()
    assert (book / "sent" / file.name).is_file()


def test_a_pasted_fill_naming_no_order_is_refused(book, approve, send, tmp_path):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    table = tmp_path / "fills.json"
    table.write_text(
        json.dumps(
            [
                {
                    "symbol": "ABC",
                    "side": "buy",
                    "quantity": 5,
                    "price": 12.4,
                    "date": TODAY,
                },
                {
                    "symbol": "XYZ",
                    "side": "buy",
                    "quantity": 5,
                    "price": 3.0,
                    "date": TODAY,
                },
            ]
        )
    )
    done = send(str(file), "--fills", str(table))
    assert done.returncode == 1
    assert "fills[1]: XYZ buy names no order of the approval" in done.stderr
    assert fill_lines(book) == []
    assert file.exists()


def test_status_participation_and_proposal_guards_name_every_problem(
    book, approve, send
):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY, adv_participation=0.5)
    document = json.loads(file.read_text())
    document["orders"].append(document["orders"][0] | {"symbol": "NEW"})
    file.write_text(json.dumps(document))
    done = send(str(file), "--dry-run")  # baseline is still research
    assert done.returncode == 1
    assert "adv_participation 0.5 exceeds limit 0.02" in done.stderr
    assert "strategy baseline is research, not live|paper" in done.stderr
    assert "orders[1]: NEW buy baseline is no order of the proposal" in done.stderr
    assert fill_lines(book) == []


def test_a_paper_sleeve_needs_dry_run(book, approve, send):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "paper")
    done = send(str(file))
    assert done.returncode == 1
    assert "strategy baseline is paper, not live" in done.stderr
