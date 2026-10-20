"""The record gate: every problem in one verdict with the book unchanged,
references resolved against live state, holdings and preferences expanded."""

from __future__ import annotations

import json

from btm_finance.ledger import Kind
from btm_finance.store import append_chained, open_book


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
                "dry_run": False,
                "id": "forged",
            }
        ],
    }
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
    assert not list((book / "ledger").glob("*.jsonl"))


def test_a_critique_lands_once_its_run_exists(book, run):
    planted = book / "ledger" / "runs.jsonl"
    append_chained(planted, [{"id": "r1", "ts": "t", "run_id": "momentum-small-r1"}])
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


def test_holdings_expand_into_opening_buy_fills(book, run):
    holdings = {
        "date": "2026-01-02",
        "positions": [
            {"symbol": "ABC", "quantity": 100, "cost_basis": 9.5},
            {"symbol": "XYZ", "quantity": 5},
        ],
    }
    code, receipt, err = batch(run, book, {"holdings": [holdings]})
    assert code == 0
    assert "XYZ has no cost_basis" in err
    assert len(receipt["new"]["holdings"]) == 2
    lines = (book / "ledger" / "fills.jsonl").read_text().splitlines()
    fills = [json.loads(line) for line in lines]
    assert [(f["symbol"], f["side"], f["strategy"], f["price"]) for f in fills] == [
        ("ABC", "buy", "opening", 9.5),
        ("XYZ", "buy", "opening", None),
    ]


def test_preferences_rewrite_the_file_whole_and_keep_extras(book, run):
    prefs = {
        "focus_sectors": ["energy"],
        "cadence": "quarterly",
        "note": "kept",
        "exclusions": {"symbols": ["XYZ"], "sectors": [], "countries": ["RU"]},
    }
    code, receipt, _ = batch(run, book, {"preferences": [prefs]})
    assert code == 0
    assert receipt["preferences"] == "rewritten"
    assert json.loads((book / "preferences.json").read_text()) == prefs


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
    assert view["families"]["baseline"]["open"][0]["id"] == hypothesis_id


def test_an_empty_batch_is_a_located_rejection(book, run):
    code, verdict, _ = batch(run, book, {})
    assert code == 1
    assert verdict["rejected"][0]["where"] == "$"
    assert open_book(str(book)).path_of(Kind.HYPOTHESIS).exists() is False
