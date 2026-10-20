"""The command surface: what start writes and refuses, check naming a missing
target, the pad inside the book, and the held-out list outside it."""

from __future__ import annotations

import json
from pathlib import Path

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
    assert hidden == {"energy": ["E0"], "tech": ["S0", "S1"]}
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


def test_the_quarter_is_deterministic_and_per_sector():
    rows = [(f"N{i}", "a") for i in range(10)] + [("X", "b")]
    chosen = stratified(rows)
    assert chosen == stratified(list(reversed(rows)))
    assert chosen == {"a": ["N0", "N1", "N2"], "b": []}


def test_check_names_a_missing_proposal_or_strategy(book, run):
    code, _, err = run(["check", str(book), "2026-01-02"])
    assert (code, "no proposal" in err) == (1, True)
    code, _, err = run(["check", str(book), "nothing"])
    assert (code, "no strategy or run named" in err) == (1, True)


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
    view = run(["check", str(book)])[1]
    assert view["pad"]["entries"] == 1


def test_schema_names_every_batch_key_and_the_pad(run):
    code, schema, _ = run(["schema"])
    assert code == 0
    assert list(schema["record_batch"]) == [
        "hypotheses",
        "critiques",
        "decisions",
        "regimes",
        "fills",
        "holdings",
        "preferences",
    ]
    assert "hunch" in schema["pad"]
