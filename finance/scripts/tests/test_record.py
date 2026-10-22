"""The record gate: every problem in one verdict with the book unchanged,
references resolved against live state, removed kinds refused by name."""

from __future__ import annotations

import json
import os
from datetime import date

import pytest
from btm_finance import store
from btm_finance.ledger import Kind
from btm_finance.models import year_after
from btm_finance.store import append_ledger, open_book

from btm_corekit import CommandError


def batch(run, book, payload):
    return run(["record", str(book), "--batch:stdin"], json.dumps(payload))


def test_every_problem_comes_back_in_one_verdict_and_nothing_moves(
    book, run, make_hypothesis
):
    payload = {
        "hypotheses": [make_hypothesis(["bad", "family"], family_id="nope")],
        "critiques": [
            {
                "kw": ["no", "run"],
                "run_id": "ghost",
                "blockers": [],
                "concerns": [],
                "by": "d",
            }
        ],
        "decisions": [
            {
                "kw": ["odd", "act"],
                "subject": "baseline",
                "action": "buy",
                "reason": "r",
            }
        ],
        "fills": [
            {
                "symbol": "ABC",
                "side": "buy",
                "quantity": 1,
                "price": 2,
                "date": "2026-01-02",
                "strategy": "baseline",
                "id": "forged",
            }
        ],
    }
    before = {p.name: p.read_bytes() for p in (book / "ledger").glob("*.jsonl")}
    code, verdict, _ = batch(run, book, payload)
    assert code == 1
    where = [problem["where"] for problem in verdict["rejected"]]
    assert where == [
        "hypotheses[0].family_id",
        "critiques[0].run_id",
        "decisions[0].action",
        "fills[0].id",
    ]
    assert verdict["unchanged"] == "book"
    after = {p.name: p.read_bytes() for p in (book / "ledger").glob("*.jsonl")}
    assert after == before


def test_a_critique_lands_once_its_run_exists(book, run):
    planted = book / "ledger" / "runs.jsonl"
    append_ledger(planted, [{"id": "r1", "ts": "t", "run_id": "momentum-small-r1"}])
    critique = {
        "kw": ["first", "pass"],
        "run_id": "momentum-small-r1",
        "blockers": ["look-ahead in join"],
        "concerns": [],
        "by": "delegate-2",
    }
    code, receipt, err = batch(run, book, {"critiques": [critique]})
    assert code == 0, err
    assert receipt["accepted"] == {"critique": 1}
    assert set(receipt["new"]["critiques"]) == {"first-pass"}


def test_holdings_are_opening_fills_naming_no_proposal(book, run):
    opening = {
        "symbol": "ABC",
        "side": "buy",
        "quantity": 100,
        "price": 9.5,
        "date": "2026-01-02",
        "strategy": "opening",
    }
    code, receipt, err = batch(run, book, {"fills": [opening]})
    assert code == 0, err
    assert receipt["accepted"] == {"fill": 1}
    (line,) = (book / "ledger" / "fills.jsonl").read_text().splitlines()
    assert json.loads(line).get("proposal") is None


@pytest.mark.parametrize("kind", ["scored", "regimes", "holdings", "preferences"])
def test_a_removed_kind_is_refused_by_name(book, run, kind):
    code, verdict, _ = batch(run, book, {kind: [{}]})
    assert code == 1
    assert verdict["rejected"][0]["where"] == kind


def test_a_decision_supersedes_only_an_existing_id(book, run, make_hypothesis):
    code, receipt, _ = batch(
        run, book, {"hypotheses": [make_hypothesis(["first", "idea"])]}
    )
    hypothesis_id = receipt["new"]["hypotheses"]["first-idea"]
    reject = {
        "kw": ["drop", "first"],
        "subject": hypothesis_id,
        "action": "reject",
        "reason": "duplicate of a known factor",
    }
    code, receipt, _ = batch(run, book, {"decisions": [reject]})
    assert code == 0
    decision_id = receipt["new"]["decisions"]["drop-first"]
    wrong = reject | {"kw": ["drop", "again"], "supersedes": "missing-id"}
    code, verdict, _ = batch(run, book, {"decisions": [wrong]})
    assert code == 1
    assert verdict["rejected"][0]["where"] == "decisions[0].supersedes"
    fixed = wrong | {"supersedes": decision_id, "action": "override"}
    assert batch(run, book, {"decisions": [fixed]})[0] == 0
    view = run(["check", str(book)])[1]
    opened = [entry["id"] for entry in view["families"]["baseline"]["open"]]
    assert hypothesis_id in opened  # beside the baseline hypothesis start made


def test_an_empty_batch_is_a_located_rejection(book, run):
    code, verdict, _ = batch(run, book, {})
    assert code == 1
    assert verdict["rejected"][0]["where"] == "$"
    path = open_book(str(book)).path_of(Kind.HYPOTHESIS)
    assert len(path.read_bytes().splitlines()) == 1  # start's baseline line only


def plant_bytes(path, extra: bytes) -> bytes:
    """A hand outside record appends bytes."""
    path.write_bytes(path.read_bytes() + extra)
    return path.read_bytes()


def test_a_line_is_id_ts_then_the_record(book, run, make_hypothesis):
    code, _, err = batch(run, book, {"hypotheses": [make_hypothesis(["one", "idea"])]})
    assert code == 0, err
    lines = (book / "ledger" / "hypotheses.jsonl").read_bytes().splitlines()
    row = json.loads(lines[1])
    assert list(row)[:2] == ["id", "ts"]
    assert row["strategy"] == "baseline"


def test_a_short_write_leaves_the_file_as_it_was(book, monkeypatch):
    path = book / "ledger" / "hypotheses.jsonl"
    before = path.read_bytes()
    real = os.write
    monkeypatch.setattr(store.os, "write", lambda fd, data: real(fd, data[:5]))
    with pytest.raises(CommandError, match="left as it was"):
        append_ledger(path, [{"id": "a", "ts": "t"}, {"id": "b", "ts": "t"}])
    assert path.read_bytes() == before


def test_a_cut_line_is_a_warning_and_record_refuses_to_append(
    book, run, make_hypothesis
):
    path = book / "ledger" / "hypotheses.jsonl"
    path.write_bytes(path.read_bytes()[:-1])
    before = path.read_bytes()
    code, view, _ = run(["check", str(book)])
    assert code == 0
    assert view["warnings"] == [
        {"file": "ledger/hypotheses.jsonl", "line": 1, "problem": "cut line"}
    ]
    code, _, err = batch(run, book, {"hypotheses": [make_hypothesis(["new", "idea"])]})
    assert code == 1
    assert "cut line" in err and "on the operator's word" in err
    assert path.read_bytes() == before


def test_an_undecodable_line_is_a_warning_never_repaired(book, run):
    path = book / "ledger" / "hypotheses.jsonl"
    after = plant_bytes(path, b"not json at all, but long enough to be cut at forty\n")
    code, view, err = run(["check", str(book)])
    assert code == 0 and "ledger warning" in err
    assert view["warnings"] == [
        {
            "file": "ledger/hypotheses.jsonl",
            "line": 2,
            "head": "not json at all, but long enough to be c",
        }
    ]
    assert path.read_bytes() == after
    assert view["incidents"] == []


def test_a_dangling_supersedes_is_a_warning(book, run):
    path = book / "ledger" / "hypotheses.jsonl"
    plant_bytes(path, b'{"id": "x1", "ts": "t", "supersedes": "ghost"}\n')
    code, view, _ = run(["check", str(book)])
    assert code == 0
    assert view["warnings"] == [
        {"file": "ledger/hypotheses.jsonl", "line": 2, "supersedes": "ghost"}
    ]


def test_record_refuses_to_append_after_an_undecodable_line(book, run, make_hypothesis):
    path = book / "ledger" / "hypotheses.jsonl"
    before = plant_bytes(path, b"[1, 2]\n")
    code, _, err = batch(run, book, {"hypotheses": [make_hypothesis(["new", "idea"])]})
    assert code == 1
    assert "line 2 is not a JSON object" in err and "on the operator's word" in err
    assert path.read_bytes() == before


def test_a_hypothesis_keeps_fields_the_gate_does_not_branch_on(
    book, run, make_hypothesis
):
    idea = make_hypothesis(["priced", "idea"], confidence=0.4, priced=12.0)
    code, _, err = batch(run, book, {"hypotheses": [idea]})
    assert code == 0, err
    line = json.loads(
        (book / "ledger" / "hypotheses.jsonl").read_text().splitlines()[-1]
    )
    assert (line["confidence"], line["priced"]) == (0.4, 12.0)


def test_retire_names_a_strategy(book, run):
    entry = {
        "kw": ["one", "retire"],
        "subject": "baseline",
        "action": "retire",
        "reason": "operator's word",
    }
    code, receipt, err = batch(run, book, {"decisions": [entry]})
    assert (code, receipt["accepted"]) == (0, {"decision": 1}), err


def test_approve_names_a_proposal_stem(book, run):
    entry = {
        "kw": ["go", "ahead"],
        "subject": "baseline",
        "action": "approve",
        "reason": "approve, go ahead",
    }
    code, verdict, _ = batch(run, book, {"decisions": [entry]})
    assert code == 1
    assert verdict["rejected"][0]["where"] == "decisions[0].subject"
    (book / "proposals" / "2026-01-30.json").write_text("{}")
    code, _, err = batch(run, book, {"decisions": [entry | {"subject": "2026-01-30"}]})
    assert code == 0, err


def test_close_names_a_hypothesis_with_realized_and_against_odds(
    book, run, make_hypothesis
):
    made = batch(run, book, {"hypotheses": [make_hypothesis(["one", "bet"])]})
    bet = made[1]["new"]["hypotheses"]["one-bet"]
    close = {
        "kw": ["bet", "ends"],
        "subject": bet,
        "action": "close",
        "reason": "kill date reached",
        "realized": 0.031,
        "against_odds": "win",
    }
    bare = {k: v for k, v in close.items() if k not in {"realized", "against_odds"}}
    wrong = [
        (bare, "decisions[0]"),
        (close | {"against_odds": "draw"}, "decisions[0].against_odds"),
        (close | {"subject": "baseline"}, "decisions[0].subject"),
        (close | {"action": "reject"}, "decisions[0]"),
    ]
    for entry, where in wrong:
        code, verdict, _ = batch(run, book, {"decisions": [entry]})
        assert code == 1, entry
        assert verdict["rejected"][0]["where"] == where, verdict
    code, receipt, err = batch(run, book, {"decisions": [close]})
    assert (code, receipt["accepted"]) == (0, {"decision": 1}), err


@pytest.mark.parametrize("action", ["diagnose", "forgo", "onboard", "pause"])
def test_a_removed_action_is_refused(book, run, action):
    entry = {"kw": ["old", "act"], "subject": "baseline", "action": action}
    code, verdict, _ = batch(run, book, {"decisions": [entry | {"reason": "r"}]})
    assert code == 1
    assert verdict["rejected"][0]["where"] == "decisions[0].action"


def test_a_cap_change_is_an_override_naming_the_book(book, run):
    book_id = json.loads((book / "book.json").read_text())["id"]
    entry = {
        "kw": ["cap", "raise"],
        "subject": book_id,
        "action": "override",
        "reason": "operator: cap 2000000",
    }
    code, receipt, err = batch(run, book, {"decisions": [entry]})
    assert (code, receipt["accepted"]) == (0, {"decision": 1}), err


def odds(kelly: float) -> dict:
    """p_win 0.6 at even payoff: Kelly is 0.6 - 0.4 / 1 = 0.2."""
    return {"p_win": 0.6, "payoff": 1.0, "horizon_days": 63, "kelly_implied": kelly}


def test_odds_off_by_two_points_are_refused_and_half_a_point_accepted(
    book, run, make_hypothesis
):
    off = make_hypothesis(["off", "odds"], odds=odds(0.22))
    code, verdict, _ = batch(run, book, {"hypotheses": [off]})
    assert code == 1
    assert [p["where"] for p in verdict["rejected"]] == ["hypotheses[0].odds"]
    near = make_hypothesis(["near", "odds"], odds=odds(0.205))
    code, receipt, err = batch(run, book, {"hypotheses": [near]})
    assert (code, receipt["accepted"]) == (0, {"hypothesis": 1}), err


def test_a_hypothesis_without_falsifier_by_is_refused(book, run, make_hypothesis):
    bare = make_hypothesis(["no", "kill"])
    del bare["falsifier_by"]
    code, verdict, _ = batch(run, book, {"hypotheses": [bare]})
    assert code == 1
    assert [p["where"] for p in verdict["rejected"]] == ["hypotheses[0].falsifier_by"]


def test_start_registers_the_baseline_with_a_kill_date_a_year_out(book):
    line = json.loads((book / "ledger" / "hypotheses.jsonl").read_text())
    made = date.fromisoformat(line["ts"][:10])
    assert date.fromisoformat(line["falsifier_by"]) == year_after(made)
    assert year_after(date(2028, 2, 29)) == date(2029, 2, 28)
