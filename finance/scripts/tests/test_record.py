"""The record gate: every problem in one verdict with the book unchanged,
references resolved against live state, holdings and preferences expanded."""

from __future__ import annotations

import json
import os

import pytest
from btm_finance import store
from btm_finance.ledger import Kind
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
                "dry_run": False,
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
    assert "cut line" in err and "operator repairs" in err
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
    assert "line 2 is not a JSON object" in err and "operator repairs" in err
    assert path.read_bytes() == before


EVENT_FIELDS = {
    "chain": "expectation-vs-outcome",
    "expectation_source": "consensus estimate the day before filing",
    "discounted": "price holds consensus; hypothesis disagrees on speed",
    "confidence": 0.4,
}


def test_an_event_family_hypothesis_lands_with_or_without_macro_fields(
    book, run, families, make_hypothesis
):
    families(book, **{"event-drift": {"trials": 8, "event": True}}, quiet={"trials": 2})
    bare = make_hypothesis(["bare", "event"], family_id="event-drift")
    code, receipt, err = batch(run, book, {"hypotheses": [bare]})
    assert code == 0, err
    assert receipt["accepted"] == {"hypothesis": 1}
    full = make_hypothesis(["full", "event"], family_id="event-drift", **EVENT_FIELDS)
    plain = make_hypothesis(["plain", "idea"], family_id="quiet")
    code, receipt, err = batch(run, book, {"hypotheses": [full, plain]})
    assert code == 0, err
    assert receipt["accepted"] == {"hypothesis": 2}
    line = json.loads(
        (book / "ledger" / "hypotheses.jsonl").read_text().splitlines()[-2]
    )
    assert line["chain"] == "expectation-vs-outcome"
    assert line["confidence"] == 0.4


def test_an_unknown_chain_is_refused_and_none_accepted(
    book, run, families, make_hypothesis
):
    families(book, **{"event-drift": {"trials": 8, "event": True}})
    odd = make_hypothesis(
        ["odd", "chain"], family_id="event-drift", **(EVENT_FIELDS | {"chain": "x"})
    )
    code, verdict, _ = batch(run, book, {"hypotheses": [odd]})
    assert code == 1
    assert [p["where"] for p in verdict["rejected"]] == ["hypotheses[0].chain"]
    none = make_hypothesis(
        ["no", "chain"], family_id="event-drift", **(EVENT_FIELDS | {"chain": "none"})
    )
    code, _, err = batch(run, book, {"hypotheses": [none]})
    assert code == 0, err


def test_diagnose_is_a_decision_action(book, run):
    diagnosis = {
        "kw": ["drift", "diagnosis"],
        "subject": "baseline",
        "action": "diagnose",
        "reason": "mechanism link broke: forced flow ended early",
        "confidence": 0.5,
    }
    code, receipt, err = batch(run, book, {"decisions": [diagnosis]})
    assert code == 0, err
    assert receipt["accepted"] == {"decision": 1}
