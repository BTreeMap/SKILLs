"""Bets scored and sleeves kept at the cap: bare `check` builds the
calibration table from `close` decisions (an older book's `scored` lines
among them), and a cap change makes a live run `stale_cap` until a
re-measure that spends no trial."""

from __future__ import annotations

import json

import pytest
from btm_finance.ledger import Kind
from btm_finance.store import append_ledger, open_book


def odds(p_win: float, payoff: float) -> dict:
    return {
        "p_win": p_win,
        "payoff": payoff,
        "horizon_days": 63,
        "kelly_implied": p_win - (1 - p_win) / payoff,
    }


def record(run, book, payload) -> dict:
    code, receipt, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps(payload)
    )
    assert code == 0, err
    return receipt


def close(subject: str, words: list[str], won: bool) -> dict:
    return {
        "kw": words,
        "subject": subject,
        "action": "close",
        "reason": "kill date reached",
        "realized": 0.04 if won else -0.03,
        "against_odds": "win" if won else "loss",
    }


def test_calibration_per_family_and_overall(book, run, make_hypothesis, families):
    families(book, carry={"trials": 3})
    bets = [
        make_hypothesis(["one", "bet"], odds=odds(0.6, 1.0)),
        make_hypothesis(["two", "bet"], odds=odds(0.8, 1.0), family_id="carry"),
        make_hypothesis(["three", "bet"], odds=odds(0.5, 2.0), family_id="carry"),
        make_hypothesis(["four", "bet"]),
    ]
    ids = record(run, book, {"hypotheses": bets})["new"]["hypotheses"]
    record(
        run,
        book,
        {
            "decisions": [
                close(ids["one-bet"], ["one", "won"], won=True),
                close(ids["two-bet"], ["two", "lost"], won=False),
            ]
        },
    )
    scored = {
        "id": "older-scored",
        "ts": "2026-09-30T00:00:00Z",
        "subject": ids["three-bet"],
        "realized_return": 0.12,
        "outcome": "carry paid",
    }
    (book / "ledger" / "scored.jsonl").write_text(json.dumps(scored) + "\n")
    table = run(["check", str(book)])[1]["calibration"]
    overall = table["overall"]
    assert overall["closed"] == 3
    assert overall["mean_p_win"] == pytest.approx((0.6 + 0.8 + 0.5) / 3)
    assert overall["win_rate"] == pytest.approx(2 / 3)
    brier = ((0.6 - 1) ** 2 + (0.8 - 0) ** 2 + (0.5 - 1) ** 2) / 3
    assert overall["brier"] == pytest.approx(brier)
    assert set(table["families"]) == {"baseline", "carry"}
    carry = table["families"]["carry"]
    assert (carry["closed"], carry["win_rate"]) == (2, pytest.approx(0.5))
    assert carry["brier"] == pytest.approx(((0.8 - 0) ** 2 + (0.5 - 1) ** 2) / 2)
    assert table["families"]["baseline"]["mean_p_win"] == pytest.approx(0.6)


def run_lines(book) -> list[dict]:
    path = book / "ledger" / "runs.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def set_cap(book, cap: int) -> None:
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["asset_cap"] = cap
    path.write_text(json.dumps(limits))


def test_a_cap_change_makes_a_live_run_stale_and_the_remeasure_is_free(synthetic, run):
    book = synthetic(seed=7)
    (book / "strategies" / "baseline" / "status").write_text("live\n")
    code, _, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    view = run(["check", str(book)])[1]
    assert view["stale_cap"] == []
    assert view["families"]["baseline"]["trials_used"] == 1
    set_cap(book, 2_000_000)
    code, view, err = run(["check", str(book)])
    [stale] = view["stale_cap"]
    assert (stale["strategy"], stale["asset_cap"], stale["now"]) == (
        "baseline",
        10_000_000,
        2_000_000,
    )
    assert "stale_cap" in err
    code, receipt, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    assert (receipt["trial"], receipt["asset_cap"]) == (False, 2_000_000)
    first, again = run_lines(book)
    assert (first["trial"], again["trial"]) == (True, False)
    assert again["scorecard"]["trials"] == first["scorecard"]["trials"] == 1
    assert again["peers"] == []
    view = run(["check", str(book)])[1]
    assert view["stale_cap"] == []
    assert view["families"]["baseline"]["trials_used"] == 1
    assert view["trials_today"]["used"] == 1
    code, receipt, err = run(["measure", str(book), "baseline"])
    assert (code, receipt["trial"]) == (0, True), err  # same cap: a trial
    assert run(["check", str(book)])[1]["families"]["baseline"]["trials_used"] == 2


def test_a_run_without_the_stamp_reads_as_the_current_cap(book, run):
    (book / "strategies" / "baseline" / "status").write_text("live\n")
    line = {"id": "old-run", "ts": "2026-01-02T00:00:00Z", "run_id": "old-run"}
    line |= {"strategy": "baseline", "family_id": "baseline"}
    append_ledger(open_book(str(book)).path_of(Kind.RUN), [line])
    assert run(["check", str(book)])[1]["stale_cap"] == []
