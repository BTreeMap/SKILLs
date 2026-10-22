"""Delegate briefs as book files: `start` seeds three with seven sections and
no Lessons, receipt pad lines naming a brief's blob id feed bare `check`'s
`briefs` table with git's history, and the operator brief never shows it."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
from btm_finance.delegation import lessons

SECTIONS = ["Task", "Reads", "Writes", "Rules", "Output", "Limit", "Lessons"]
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="no git")
IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false")


def test_start_seeds_three_briefs_with_seven_sections(book):
    found = sorted(p.name for p in (book / "delegates").iterdir())
    assert found == ["author.md", "bet.md", "critique.md"]
    for path in (book / "delegates").iterdir():
        text = path.read_text()
        assert re.findall(r"^## (\w+)", text, flags=re.MULTILINE) == SECTIONS
        assert lessons(text) == 0
        assert not re.search(r"\d{4}-\d{2}-\d{2}", text)
        assert text.rstrip().endswith("## Lessons")
        unit = path.stem
        assert f'"unit": "{unit}"' in text
        assert f"git hash-object delegates/{unit}.md" in text


def git(book: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(book), *IDENTITY, *argv],
        capture_output=True,
        check=True,
        text=True,
    )
    return done.stdout.strip()


def receipt(blob: str, status: str = "done", friction: str = "") -> dict:
    return {
        "ts": "2026-10-01T10:00:00Z",
        "type": "receipt",
        "unit": "bet",
        "brief": blob,
        "agent": "bet-1",
        "status": status,
        "wrote": [],
        "ids": [],
        "summary": "s",
        "next": "n",
        "friction": friction,
    }


@needs_git
def test_receipt_lines_and_git_feed_the_briefs_table(book, run):
    git(book, "add", "delegates")
    git(book, "commit", "-q", "-m", "seed briefs")
    seeded = git(book, "hash-object", "delegates/bet.md")
    rows = {row["unit"]: row for row in run(["check", str(book)])[1]["briefs"]}
    assert rows["bet"]["dispatches"] == 0
    assert (rows["bet"]["clean"], rows["bet"]["last_lesson"]) == (None, None)
    path = book / "delegates" / "bet.md"
    path.write_text(
        path.read_text() + "\n- Name the fetch cap. (receipt 2026-10-01T10:00:00Z)\n"
    )
    git(book, "commit", "-q", "-am", "bet brief: lesson from receipt")
    lesson = git(book, "log", "-1", "--format=%cs")
    patched = git(book, "hash-object", "delegates/bet.md")
    pad = [
        receipt(seeded),
        receipt(seeded, status="partial"),
        receipt(seeded, friction="no fetch cap"),
        receipt(patched),
    ]
    pad += [{"ts": "2026-10-02T00:00:00Z", "type": "hunch", "unit": "bet"}]
    scratch = book / "ledger" / "pad" / "scratch.jsonl"
    scratch.write_text("".join(json.dumps(row) + "\n" for row in pad))
    view = run(["check", str(book)])[1]
    rows = {row["unit"]: row for row in view["briefs"]}
    assert set(rows) == {"bet", "author", "critique"}
    bet = rows["bet"]
    assert (bet["dispatches"], bet["on_current"]) == (4, 1)
    assert bet["clean"] == pytest.approx(0.5)
    assert bet["clean_last_ten"] == pytest.approx(0.5)
    assert bet["last_lesson"] == lesson
    assert date.fromisoformat(lesson)
    assert (rows["author"]["dispatches"], rows["author"]["last_lesson"]) == (0, None)
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert not any("bet" in line or "clean" in line for line in lines)
