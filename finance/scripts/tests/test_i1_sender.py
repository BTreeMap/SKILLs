"""Invariant 1: no broker adapter in reach. A dry run of the scaffolded sender
records fills through `record` and calls no adapter; a real send stops at the
stub before any fill lands."""

from __future__ import annotations

import ast
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

TODAY = datetime.now(UTC).date().isoformat()
NO_ADAPTER = "no broker adapter installed: edit bin/send"


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
    tree = ast.parse((book / "bin" / "send").read_text())
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


@pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pty")
def test_dry_run_records_fills_and_a_real_send_stops_at_the_stub(book, approve, send):
    import pty  # noqa: PLC0415 - POSIX-only, imported past the skip

    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "paper")
    dry = send(str(file), "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert NO_ADAPTER not in dry.stderr
    fills = fill_lines(book)
    assert [(f["symbol"], f["price"], f["dry_run"]) for f in fills] == [
        ("ABC", 12.5, True)
    ]
    assert file.exists()  # a dry run moves nothing
    assert not any((book / "sent").iterdir())

    set_status(book, "live")
    primary, secondary = pty.openpty()
    try:
        os.write(primary, b"yes\n")
        real = send(str(file), stdin=secondary)
    finally:
        os.close(secondary)
        os.close(primary)
    assert real.returncode == 1
    assert NO_ADAPTER in real.stderr
    assert fill_lines(book) == fills  # nothing recorded past the stub
    assert file.exists()


def test_a_real_send_without_a_terminal_is_refused(book, approve, send):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    done = send(str(file))
    assert done.returncode == 1
    assert "needs a terminal" in done.stderr
    assert fill_lines(book) == []


def test_status_and_participation_guards_name_every_problem(book, approve, send):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY, adv_participation=0.5)
    done = send(str(file), "--dry-run")  # baseline is still research
    assert done.returncode == 1
    assert "adv_participation 0.5 exceeds limit 0.02" in done.stderr
    assert "strategy baseline is research, not live|paper" in done.stderr
    assert fill_lines(book) == []
