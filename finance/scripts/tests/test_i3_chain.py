"""Invariant 3: the ledger is append-only; an edited line breaks the chain and
bare check reports it by file and line, repairing nothing."""

from __future__ import annotations

import json
from pathlib import Path

from btm_finance.ledger import audit, chained, line_digest


def record_two(book: Path, run, make_hypothesis) -> Path:
    batch = {
        "hypotheses": [
            make_hypothesis(["first", "idea"]),
            make_hypothesis(["second", "idea"]),
        ]
    }
    code, document, err = run(["record", str(book), "--batch:stdin"], json.dumps(batch))
    assert code == 0, err
    assert set(document["new"]["hypotheses"]) == {"first-idea", "second-idea"}
    return book / "ledger" / "hypotheses.jsonl"


def test_each_prev_is_the_digest_of_the_previous_line(book, run, make_hypothesis):
    lines = record_two(book, run, make_hypothesis).read_bytes().splitlines()
    baseline, first, second = (json.loads(line) for line in lines)
    assert baseline["prev"] is None  # start registers the baseline hypothesis
    assert first["prev"] == line_digest(lines[0])
    assert second["prev"] == line_digest(lines[1])
    assert list(first)[:3] == ["id", "ts", "prev"]


def test_an_intact_chain_reports_no_break(book, run, make_hypothesis):
    record_two(book, run, make_hypothesis)
    code, view, _ = run(["check", str(book)])
    assert code == 0
    assert view["incidents"]["ledger"] == []
    assert view["chain"] == {"files": 1, "lines": 3, "breaks": 0}


def test_one_edited_byte_is_reported_with_file_and_line(book, run, make_hypothesis):
    path = record_two(book, run, make_hypothesis)
    before = path.read_bytes()
    edited = before.replace(b"12 months", b"13 months", 1)  # line 2: first idea
    assert edited != before
    path.write_bytes(edited)
    code, view, err = run(["check", str(book)])
    assert code == 0
    assert "ledger break" in err
    breaks = view["incidents"]["ledger"]
    assert [(b["file"], b["line"]) for b in breaks] == [("ledger/hypotheses.jsonl", 3)]
    assert path.read_bytes() == edited  # reported, never repaired
    assert "restore from backup" in view["next"]


def test_a_cut_write_and_a_removed_first_line_are_both_named():
    lines = chained(None, [{"id": "a", "ts": "t"}, {"id": "b", "ts": "t"}])
    cut = lines[0] + b"\n" + lines[1][:-3]
    assert [(b.line, b.problem.split(":")[0]) for b in audit("f", cut)] == [
        (2, "line is not a JSON object"),
        (2, "last line has no newline"),
    ]
    assert [b.line for b in audit("f", lines[1] + b"\n")] == [1]


def test_record_refuses_to_append_after_a_cut_line(book, run, make_hypothesis):
    path = record_two(book, run, make_hypothesis)
    path.write_bytes(path.read_bytes()[:-1])
    batch = {"hypotheses": [make_hypothesis(["third", "idea"])]}
    code, _, err = run(["record", str(book), "--batch:stdin"], json.dumps(batch))
    assert code == 1
    assert "cut line" in err
