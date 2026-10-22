"""A started book per test, under an isolated state root, plus a runner."""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from btm_finance.cli import main
from btm_finance.synthetic import make_book

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


KILL_DATE = "2099-12-31"
"""Far enough out that no fixture hypothesis turns overdue."""
ODDS: dict[str, Any] = {
    "p_win": 0.55,
    "payoff": 1.0,
    "horizon_days": 63,
    "kelly_implied": 0.1,
}
"""A modest stated bet every fixture hypothesis carries."""


def hypothesis(kw: list[str], **overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "kw": kw,
        "strategy": "baseline",
        "family_id": "baseline",
        "falsifier": "net Sharpe under the baseline's over 12 months",
        "counterparty": "index funds rebalancing on schedule",
        "min_holding_days": 21,
        "falsifier_by": KILL_DATE,
        "odds": ODDS,
    }
    return entry | overrides


@pytest.fixture
def make_hypothesis() -> Callable[..., dict[str, Any]]:
    return hypothesis


@pytest.fixture
def synthetic(tmp_path: Path) -> Callable[..., Path]:
    """A started book holding a seeded synthetic panel; see `make_book`."""

    def make(seed: int = 7, **options: Any) -> Path:
        root = tmp_path / f"synthetic-{seed}"
        make_book(root, seed, **options)
        return root

    return make


STRATEGY: dict[str, Any] = {
    "params": {},
    "rebalance": "monthly",
    "holding_days": 21,
    "long_only": False,
    "family_id": "baseline",
}


def write_strategy(book: Path, name: str, source: str, **config: Any) -> Path:
    """`strategies/<name>/` with `source` as signal.py and `config` over the
    default monthly long-short config."""
    folder = book / "strategies" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "signal.py").write_text(source)
    (folder / "config.json").write_text(json.dumps(STRATEGY | config))
    (folder / "status").write_text("research\n")
    return folder


@pytest.fixture
def plant(run: Run) -> Callable[..., str]:
    """Write a strategy, then register its hypothesis; returns the id."""

    def make(
        book: Path,
        name: str,
        source: str,
        hypothesis: dict[str, Any] | None = None,
        **config: Any,
    ) -> str:
        folder = write_strategy(book, name, source, **config)
        settings = json.loads((folder / "config.json").read_text())
        entry = {
            "kw": [*name.split("-"), "idea"],
            "strategy": name,
            "family_id": settings["family_id"],
            "falsifier": "net Sharpe at or below zero out of sample",
            "counterparty": "planted by the test",
            "min_holding_days": settings["holding_days"],
            "falsifier_by": KILL_DATE,
            "odds": ODDS,
        } | (hypothesis or {})
        code, receipt, err = run(
            ["record", str(book), "--batch:stdin"], json.dumps({"hypotheses": [entry]})
        )
        assert code == 0, err
        return str(next(iter(receipt["new"]["hypotheses"].values())))

    return make


def set_families(book: Path, **families: dict[str, Any]) -> None:
    """A hand edit to `limits.json` adding or replacing families."""
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["families"] |= families
    path.write_text(json.dumps(limits))


@pytest.fixture
def families() -> Callable[..., None]:
    return set_families
