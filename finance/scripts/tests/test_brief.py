"""Bare `check` warnings for kill dates and unscored bets, the trial a
superseding hypothesis spends, and `check --brief`'s twelve-line budget."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from btm_finance.ledger import Kind
from btm_finance.store import append_ledger, open_book

SCORE = {
    "kw": ["bet", "scored"],
    "resolved": "2026-09-30",
    "outcome": "edge gone before the kill date",
    "realized_return": -0.01,
    "brier": 0.3,
    "log_score": -0.8,
    "attribution": {
        "market": 0.0,
        "factor": -0.005,
        "currency": 0.0,
        "idiosyncratic": 0.0,
        "costs": -0.005,
    },
}
ODDS = {"p_win": 0.55, "payoff": 1.2, "horizon_days": 30, "kelly_implied": 0.175}


def record(run, book, payload):
    code, receipt, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps(payload)
    )
    assert code == 0, err
    return receipt


def late(view, problem):
    return [w for w in view["warnings"] if w.get("problem") == problem]


def test_a_past_kill_date_warns_until_a_scored_line_lands(book, run, make_hypothesis):
    stale = make_hypothesis(["old", "bet"], falsifier_by="2020-01-01")
    made = record(run, book, {"hypotheses": [stale]})["new"]["hypotheses"]["old-bet"]
    view = run(["check", str(book)])[1]
    [warned] = late(view, "overdue")
    assert (warned["hypothesis"], warned["falsifier_by"]) == (made, "2020-01-01")
    assert warned["days_overdue"] > 2000
    assert "falsifier_by" in view["next"]
    record(run, book, {"scored": [SCORE | {"subject": made}]})
    assert late(run(["check", str(book)])[1], "overdue") == []


def test_a_reject_naming_the_hypothesis_clears_overdue(book, run, make_hypothesis):
    stale = make_hypothesis(["old", "bet"], falsifier_by="2020-01-01")
    made = record(run, book, {"hypotheses": [stale]})["new"]["hypotheses"]["old-bet"]
    reject = {"kw": ["kill", "it"], "subject": made, "action": "reject", "reason": "r"}
    record(run, book, {"decisions": [reject]})
    assert late(run(["check", str(book)])[1], "overdue") == []


def test_a_promoted_bet_past_its_horizon_warns_until_scored(book, run, make_hypothesis):
    bet = make_hypothesis(["timed", "bet"], odds=ODDS)
    made = record(run, book, {"hypotheses": [bet]})["new"]["hypotheses"]["timed-bet"]
    promote = {
        "id": "promote-baseline-test",
        "ts": "2026-01-02T00:00:00Z",
        "kw": ["go", "baseline"],
        "subject": "baseline",
        "action": "promote",
        "reason": "operator promoted",
    }
    append_ledger(open_book(str(book)).path_of(Kind.DECISION), [promote])
    [warned] = late(run(["check", str(book)])[1], "unscored")
    assert (warned["hypothesis"], warned["due"]) == (made, "2026-02-01")
    record(run, book, {"scored": [SCORE | {"subject": made}]})
    assert late(run(["check", str(book)])[1], "unscored") == []


def test_a_superseding_hypothesis_spends_a_trial(book, run, make_hypothesis):
    first = record(run, book, {"hypotheses": [make_hypothesis(["one", "bet"])]})
    made = first["new"]["hypotheses"]["one-bet"]
    assert run(["check", str(book)])[1]["families"]["baseline"]["trials_used"] == 0
    longer = make_hypothesis(["one", "longer"], supersedes=made)
    record(run, book, {"hypotheses": [longer]})
    assert run(["check", str(book)])[1]["families"]["baseline"]["trials_used"] == 1


def proposals(book, days):
    folder = book / "proposals"
    folder.mkdir(exist_ok=True)
    for day in days:
        sleeves = {
            "baseline": {"run_id": "none", "weight": 0.1, "sharpe_net": 0.6},
            "drift": {"run_id": "none", "weight": 0.02, "tier": "probe"},
        }
        (folder / f"{day}.json").write_text(json.dumps({"sleeves": sleeves}))


def incidents(book, count):
    today = datetime.now(UTC).date().isoformat()
    rows = [
        {
            "id": f"live-{k}",
            "ts": f"{today}T00:00:00Z",
            "kind": ("drawdown", "tracking")[k % 2],
            "strategy": ("baseline", "drift", "carry")[k % 3],
            "as_of": today,
        }
        for k in range(count)
    ]
    append_ledger(open_book(str(book)).path_of(Kind.INCIDENT), rows)


def test_the_brief_fits_three_proposals_and_five_incidents_in_twelve_lines(book, run):
    proposals(book, ["2026-07-31", "2026-08-31", "2026-09-30"])
    incidents(book, 5)
    code, brief, _ = run(["check", str(book), "--brief"])
    assert code == 0
    lines = brief["lines"]
    assert len(lines) == 7
    assert all("\n" not in line for line in lines)
    assert lines[0] == "regime: no regime"
    assert lines[1].startswith("proposal 2026-07-31")
    assert "baseline - w 0.1 odds none sharpe_net 0.6" in lines[1]
    assert "drift probe w 0.02 odds none dsr null" in lines[1]
    assert lines[4].startswith("breaches, last 7 days: ")
    assert lines[4].count(",") == 5  # five strategy-kind pairs after the colon
    assert lines[5] == "overdue 0, unscored 0"
    assert lines[6] == f"next: {brief['next']}"


def test_more_proposals_than_fit_collapse_to_a_count_and_the_newest_two(book, run):
    days = [f"2026-{month:02d}-01" for month in range(1, 11)]
    proposals(book, days)
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert len(lines) == 7
    assert lines[1].startswith("10 open proposals")
    assert lines[2].startswith("proposal 2026-10-01")
    assert lines[3].startswith("proposal 2026-09-01")
