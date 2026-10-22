"""Bare `check` `evolution`: dispatch and friction counts per brief from
receipt pad lines, run counts per `lib/` module from run lines, and the idle
list from commit dates; derived on every call, never written."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from btm_finance.evolution import evolution

PAD = ("ledger", "pad", "scratch.jsonl")
TODAY = date(2026, 10, 21)


def receipt(unit: str, ts: str, friction: str = "") -> dict:
    return {"type": "receipt", "unit": unit, "ts": ts, "friction": friction}


def test_counts_come_from_planted_receipts_and_runs():
    found = evolution(
        briefs=["author", "critique"],
        pad=[
            receipt("author", "2026-10-01T00:00:00+00:00"),
            receipt("author", "2026-10-05T00:00:00+00:00", "brief named no family"),
            receipt("ghost", "2026-10-06T00:00:00+00:00"),
            {"type": "hunch", "unit": "author", "ts": "2026-10-07T00:00:00+00:00"},
        ],
        runs=[
            {"ts": "2026-09-01T00:00:00+00:00", "code_paths": ["lib/tilt.py"]},
            {"ts": "2026-10-02T00:00:00+00:00", "code_paths": ["lib/tilt.py"]},
        ],
        lib=["lib/tilt.py", "lib/unused.py"],
        tools=["tools/fetch-filings.py"],
        commits={
            "lib/tilt.py": "2026-01-01T00:00:00+00:00",
            "lib/unused.py": "2026-07-01T00:00:00+00:00",
            "tools/fetch-filings.py": "2026-01-02T00:00:00+00:00",
        },
        today=TODAY,
        idle_days=90,
    )
    assert found["briefs"] == {
        "author": {
            "dispatches": 2,
            "frictions": 1,
            "last": "2026-10-05T00:00:00+00:00",
        },
        "critique": {"dispatches": 0, "frictions": 0, "last": None},
    }
    assert found["lib"]["lib/tilt.py"] == {
        "runs": 2,
        "last_run": "2026-10-02",
        "last_commit": "2026-01-01",
    }
    assert found["tools"] == {"tools/fetch-filings.py": {"last_commit": "2026-01-02"}}
    assert found["idle"] == ["lib/unused.py", "tools/fetch-filings.py"]


def test_an_uncommitted_file_is_never_idle():
    found = evolution(
        briefs=[],
        pad=[],
        runs=[],
        lib=["lib/draft.py"],
        tools=[],
        commits={},
        today=TODAY,
        idle_days=90,
    )
    assert found["idle"] == []


def test_check_lists_a_stale_module_as_idle(book, run, commit, monkeypatch):
    (book / "lib" / "old.py").write_text("X = 1\n")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2020-01-01T00:00:00+00:00")
    commit(book, "lib/old.py", subject="feat: old module")
    monkeypatch.delenv("GIT_COMMITTER_DATE")
    (book / "lib" / "fresh.py").write_text("X = 2\n")
    commit(book, "lib/fresh.py", subject="feat: fresh module")
    line = receipt("author", "2026-10-01T00:00:00+00:00", "no family named")
    with book.joinpath(*PAD).open("a", encoding="utf-8") as pad:
        pad.write(json.dumps(line) + "\n")
    code, view, err = run(["check", str(book)])
    assert code == 0, err
    found = view["evolution"]
    assert found["idle"] == ["lib/old.py"]
    assert found["lib"]["lib/old.py"]["last_commit"] == "2020-01-01"
    assert found["briefs"]["author"]["frictions"] == 1
    assert "evolution" not in json.dumps(view["warnings"])
    assert not any(Path(book).rglob("evolution*"))
