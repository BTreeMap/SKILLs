"""The command surface: what start writes and refuses, later stages refused by
name, the pad inside the book, and the held-out list outside it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from btm_finance.scaffold import stratified


def test_start_writes_the_book_and_the_held_out_list_outside_it(tmp_path, run):
    universe = tmp_path / "names.csv"
    rows = [f"S{i},tech" for i in range(8)] + [f"E{i},energy" for i in range(4)]
    universe.write_text("symbol,sector\n" + "\n".join(rows) + "\n")
    code, receipt, _ = run(
        ["start", str(tmp_path / "b"), "--universe:file", str(universe)]
    )
    assert code == 0
    book = tmp_path / "b"
    for name in ("limits.json", "preferences.json", "book.json", "bin/send"):
        assert (book / name).is_file(), name
    assert (book / "strategies" / "baseline" / "status").read_text() == "research\n"
    assert (book / "universe.csv").read_text() == universe.read_text()
    assert receipt["held_out"]["names"] == 3
    hidden = json.loads(Path(receipt["held_out"]["path"]).read_text())
    assert hidden["by_sector"]["tech"] == {"held_out": 2, "universe": 8}
    assert "S0" not in json.dumps(hidden)  # digests only, no symbol
    assert not str(receipt["held_out"]["path"]).startswith(str(book))
    deny = json.loads((book / ".claude" / "settings.json").read_text())["permissions"][
        "deny"
    ]
    assert deny[0] == "Bash(*bin/send*)"
    assert len(deny) == 6


def test_start_without_a_universe_signals_an_empty_list(book, run):
    code, _, err = run(["start", str(book.parent / "other")])
    assert code == 0
    assert "held-out list empty" in err


def test_start_refuses_a_directory_holding_limits(book, run):
    code, _, err = run(["start", str(book)])
    assert code == 1
    assert "already holds limits.json" in err


def test_the_quarter_is_stable_for_one_salt_and_per_sector():
    rows = [(f"N{i}", "a") for i in range(10)] + [("X", "b")]
    chosen = stratified(rows, "salt")
    assert chosen == stratified(list(reversed(rows)), "salt")
    assert {sector: len(names) for sector, names in chosen.items()} == {"a": 3, "b": 0}


@pytest.mark.parametrize(
    ("argv", "stage"),
    [
        (["score", "B", "baseline"], "stage 3b"),
        (["advise", "B", "2026-01-02"], "stage 4"),
    ],
)
def test_later_verbs_are_refused_by_stage(run, argv, stage):
    code, _, err = run(argv)
    assert code == 1
    assert stage in err


def test_check_refuses_a_target_and_live_by_stage(book, run):
    code, _, err = run(["check", str(book), "baseline"])
    assert (code, "stage 3b" in err) == (1, True)
    code, _, err = run(["check", str(book), "--live"])
    assert (code, "stage 5" in err) == (1, True)


def test_verbs_refuse_a_path_without_a_book(tmp_path, run):
    code, _, err = run(["check", str(tmp_path)])
    assert code == 1
    assert "no book at" in err


def test_the_pad_lives_inside_the_book(book, run):
    code, receipt, _ = run(["write", str(book), "--entry:stdin"], '{"type": "hunch"}')
    assert (code, receipt["written"]) == (0, "j1")
    assert (book / "ledger" / "pad" / "scratch.jsonl").is_file()
    code, found, _ = run(["read", str(book), "--type", "hunch"])
    assert found["shown"] == 1
    assert run(["check", str(book)])[1]["chain"]["files"] == 0  # pad is not chained


def test_schema_names_every_batch_key_and_the_pad(run):
    code, schema, _ = run(["schema"])
    assert code == 0
    assert list(schema["record_batch"]) == [
        "hypotheses",
        "critiques",
        "decisions",
        "fills",
        "holdings",
        "preferences",
    ]
    assert "hunch" in schema["pad"]
