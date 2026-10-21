"""The always-on loop: `measure` refuses past `limits.trials_per_day`
writing nothing, bare `check` reports the heartbeat and warns only on a
stale one, quiet hours wrap midnight, and three unattended wake-ups end in
a brief with no trial spent past the cap."""

from __future__ import annotations

import json
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pytest
from btm_finance.brief import Reply
from btm_finance.heartbeat import START, is_quiet
from btm_finance.models import Preferences, QuietHours
from pydantic import ValidationError

STALE = "heartbeat stale"
PAD = ("ledger", "pad", "scratch.jsonl")


def run_count(book: Path) -> int:
    files = [book / "ledger" / "runs.jsonl", *(book / "ledger" / "runs").glob("*")]
    return sum(len(f.read_text().splitlines()) for f in files if f.is_file())


def set_limit(book: Path, key: str, value: object) -> None:
    path = book / "limits.json"
    path.write_text(json.dumps(json.loads(path.read_text()) | {key: value}))


def beat(book: Path, ts: datetime, item: str, outcome: str, minutes: int = 45) -> None:
    """One `heartbeat` pad line, appended with the agent's own file tools."""
    line = {
        "ts": ts.isoformat(),
        "type": "heartbeat",
        "item": item,
        "outcome": outcome,
        "next_wake": (ts + timedelta(minutes=minutes)).isoformat(),
    }
    with book.joinpath(*PAD).open("a", encoding="utf-8") as pad:
        pad.write(json.dumps(line) + "\n")


def stale(view: dict) -> list[dict]:
    return [w for w in view["warnings"] if w.get("problem") == STALE]


def test_measure_refuses_past_the_daily_cap_and_writes_no_line(synthetic, run):
    book = synthetic(seed=7)
    set_limit(book, "trials_per_day", 1)
    code, _, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    assert run_count(book) == 1
    code, _, err = run(["measure", str(book), "baseline"])
    assert code == 1
    assert "limits.trials_per_day 1" in err
    assert run_count(book) == 1
    view = run(["check", str(book)])[1]
    assert view["trials_today"] == {"used": 1, "cap": 1}
    code, _, err = run(["measure", str(book), "baseline", "--held-out"])
    assert code == 0, err
    assert run_count(book) == 2


def test_a_fresh_book_starts_the_heartbeat_and_a_stale_one_warns(book, run):
    view = run(["check", str(book)])[1]
    assert view["warnings"] == []
    assert view["heartbeat"] == {
        "last": None,
        "minutes_since": None,
        "stale": False,
        "quiet": False,
    }
    assert view["next"].startswith(START)
    old = datetime.now(UTC) - timedelta(hours=3)
    beat(book, old, "tier 0: check", "nothing due")
    code, view, err = run(["check", str(book)])
    assert code == 0
    [warning] = stale(view)
    assert warning["limit"] == 90 and warning["minutes_since"] >= 180
    assert view["heartbeat"]["stale"] is True
    assert "heartbeat" in err
    assert not view["next"].startswith(START)
    beat(book, datetime.now(UTC), "tier 0: check", "nothing due")
    view = run(["check", str(book)])[1]
    assert stale(view) == []
    assert view["heartbeat"]["minutes_since"] == 0


@pytest.mark.parametrize(
    ("clock", "quiet"),
    [
        (time(23, 30), True),
        (time(0, 0), True),
        (time(5, 59), True),
        (time(6, 0), False),
        (time(12, 0), False),
        (time(22, 0), True),
        (time(21, 59), False),
    ],
)
def test_quiet_hours_wrap_midnight(clock, quiet):
    assert is_quiet(QuietHours(start="22:00", end="06:00"), clock) is quiet


def test_quiet_hours_inside_a_day_empty_or_absent():
    lunch = QuietHours(start="12:00", end="13:00")
    assert is_quiet(lunch, time(12, 30))
    assert not is_quiet(lunch, time(13, 0))
    assert not is_quiet(QuietHours(start="08:00", end="08:00"), time(8, 0))
    assert not is_quiet(None, time(3, 0))
    with pytest.raises(ValidationError):
        QuietHours(start="24:00", end="06:00")
    held = Preferences.model_validate(
        {"focus_sectors": [], "exclusions": {}, "cadence": "monthly"}
    )
    assert (held.heartbeat_minutes, held.quiet_hours) == (45, None)


def test_three_unattended_wakes_end_in_a_brief_within_the_cap(synthetic, run):
    book = synthetic(seed=7)
    first = datetime.now(UTC) - timedelta(minutes=90)
    for wake in range(3):
        code, view, err = run(["check", str(book)])  # tier 0, every wake
        assert code == 0, err
        assert view["next"].startswith(START) is (wake == 0)
        if wake == 0:  # tier 3, once
            code, _, err = run(["measure", str(book), "baseline"])
            assert code == 0, err
            item, outcome = "tier 3: measure baseline", "one trial spent"
        else:
            item, outcome = "tier 2: book hygiene", "INDEX.md current"
        beat(book, first + timedelta(minutes=45 * wake), item, outcome)
    code, brief, err = run(["check", str(book), "--brief"])
    assert code == 0, err
    assert 1 <= len(brief["lines"]) <= 12
    assert brief["lines"][-1] == Reply.NOTHING.value
    view = run(["check", str(book)])[1]
    used = view["trials_today"]
    assert used["used"] == run_count(book) == 1
    assert used["used"] <= used["cap"] == 3
    assert stale(view) == []
    beats = [
        json.loads(line)
        for line in book.joinpath(*PAD).read_text().splitlines()
        if json.loads(line)["type"] == "heartbeat"
    ]
    assert len(beats) == 3
    assert all({"ts", "item", "outcome", "next_wake"} <= b.keys() for b in beats)
