"""A started book per test, under an isolated state root, plus a runner."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from btm_finance.cli import main

Run = Callable[..., tuple[int, Any, str]]


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every test owns its own state root, so no held-out list leaks across."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    return tmp_path


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Run:
    """One command in process: (exit code, parsed stdout or None, stderr)."""

    def invoke(argv: list[str], stdin: str | None = None) -> tuple[int, Any, str]:
        original = sys.stdin
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        try:
            code = main(argv)
        finally:
            sys.stdin = original
        captured = capsys.readouterr()
        document = json.loads(captured.out) if captured.out.strip() else None
        return code, document, captured.err

    return invoke


@pytest.fixture
def book(tmp_path: Path, run: Run) -> Path:
    root = tmp_path / "book"
    code, _, err = run(["start", str(root)])
    assert code == 0, err
    return root


def hypothesis(kw: list[str], **overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "kw": kw,
        "strategy": "baseline",
        "family_id": "baseline",
        "capacity_class": "in_band",
        "falsifier": "net Sharpe under the baseline's over 12 months",
        "counterparty": "index funds rebalancing on schedule",
        "min_holding_days": 21,
    }
    return entry | overrides


@pytest.fixture
def make_hypothesis() -> Callable[..., dict[str, Any]]:
    return hypothesis


ORDER: dict[str, Any] = {
    "symbol": "ABC",
    "side": "buy",
    "quantity": 10,
    "price": 12.5,
    "strategy": "baseline",
    "adv_participation": 0.001,
}


def approval(where: Path, day: str, **order: Any) -> Path:
    """One approval file holding one order, `order` overriding the default."""
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(json.dumps({"date": day, "orders": [ORDER | order]}))
    return where


@pytest.fixture
def approve() -> Callable[..., Path]:
    return approval


@pytest.fixture
def send(book: Path) -> Callable[..., Any]:
    """The scaffolded `bin/send`, run as the operator would: its own process."""

    def invoke(*args: str, stdin: Any = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(book / "bin" / "send"), *args],
            stdin=stdin if stdin is not None else subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

    return invoke
