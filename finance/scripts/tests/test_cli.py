"""The command surface: what start writes and refuses, check naming a missing
target, the pad count, check --schema, and the held-out list outside it."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from btm_finance import git
from btm_finance.api import Market
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
    for name in ("limits.json", "preferences.json", "book.json"):
        assert (book / name).is_file(), name
    assert not (book / "bin").exists() and not (book / "sent").exists()
    assert (book / "strategies" / "baseline" / "status").read_text() == "research\n"
    assert (book / "universe.csv").read_text() == universe.read_text()
    assert receipt["held_out"]["names"] == 3
    hidden = json.loads(Path(receipt["held_out"]["path"]).read_text())
    assert hidden == {"energy": ["E0"], "tech": ["S0", "S1"]}
    assert not str(receipt["held_out"]["path"]).startswith(str(book))
    assert not (book / ".claude").exists()


def test_start_writes_the_held_out_list_where_the_operator_names(tmp_path, run):
    universe = tmp_path / "names.csv"
    universe.write_text("symbol,sector\nA,x\nB,x\nC,x\nD,x\n")
    hidden = tmp_path / "vault" / "held.json"
    code, receipt, err = run(
        [
            "start",
            str(tmp_path / "b"),
            "--universe:file",
            str(universe),
            "--held-out",
            str(hidden),
        ]
    )
    assert code == 0, err
    assert receipt["held_out"] == {"path": str(hidden.resolve()), "names": 1}
    assert json.loads(hidden.read_text()) == {"x": ["A"]}
    marker = json.loads((tmp_path / "b" / "book.json").read_text())
    assert marker["held_out"] == str(hidden.resolve())


def test_start_refuses_a_held_out_path_inside_the_book(tmp_path, run):
    book = tmp_path / "b"
    code, _, err = run(["start", str(book), "--held-out", str(book / "h.json")])
    assert code == 1
    assert "inside the book" in err
    assert not (book / "limits.json").exists()


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


def test_bare_check_counts_lines_the_agent_appends_to_the_pad(book, run):
    pad = book / "ledger" / "pad" / "scratch.jsonl"
    assert run(["check", str(book)])[1]["pad"]["entries"] == 0
    pad.write_text('{"ts": "2026-01-02T00:00:00Z", "type": "hunch"}\n')
    assert run(["check", str(book)])[1]["pad"]["entries"] == 1


def test_the_pruned_verbs_are_gone(book, run):
    for verb in ("onboard", "schema", "write", "read"):
        code, _, err = run([verb, str(book)])
        assert code == 1 and "invalid choice" in err, verb


def test_check_schema_without_a_book_prints_every_kind(run):
    code, schema, _ = run(["check", "--schema"])
    assert code == 0
    assert list(schema) == [
        "record",
        "run",
        "answers",
        "pad",
        "receipt",
        "approval",
        "strategy",
    ]
    assert list(schema["record"]["record_batch"]) == [
        "hypotheses",
        "critiques",
        "decisions",
        "scored",
        "regimes",
        "fills",
        "holdings",
        "preferences",
    ]
    assert "hunch" in schema["pad"]["types"]
    assert "known" not in schema["pad"]["types"]


def test_check_schema_strategy_names_every_public_market_accessor(run):
    code, schema, _ = run(["check", "--schema", "strategy"])
    assert (code, list(schema)) == (0, ["strategy"])
    contract = schema["strategy"]
    public = {
        name
        for name in dir(Market)
        if not name.startswith("_")
        and not isinstance(inspect.getattr_static(Market, name), classmethod)
    }
    assert public >= {"close", "names", "day", "events", "factor"}
    assert set(contract["market"]) == public | {"Market"}
    assert "signal(market, params)" in contract["signal"]
    assert "import lib.<module>" in contract["signal"]
    assert set(contract["config"]["properties"]) == {
        "params",
        "rebalance",
        "holding_days",
        "long_only",
        "family_id",
    }


def test_check_schema_with_a_kind_prints_that_kind_only(book, run):
    code, schema, _ = run(["check", "--schema", "approval"])
    assert (code, list(schema)) == (0, ["approval"])
    assert "adv_participation" in schema["approval"]["rules"]
    assert run(["check", str(book), "--schema", "pad"])[1].keys() == {"pad"}
    code, _, err = run(["check", "--schema", "fills"])
    assert code == 1 and "record|run|answers|pad|receipt|approval" in err
    code, _, err = run(["check"])
    assert code == 1 and "only --schema runs without one" in err


def test_start_inits_main_commits_and_leaves_a_clean_tree(
    tmp_path_factory, monkeypatch, run
):
    """Outside any repository `start` runs `git init`; the identity comes
    from this process's environment, never a config file."""
    for key in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{key}_NAME", "Test Agent")
        monkeypatch.setenv(f"GIT_{key}_EMAIL", "agent@example.invalid")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "commit.gpgsign")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "false")
    root = tmp_path_factory.mktemp("alone") / "b"
    code, receipt, err = run(["start", str(root)])
    assert code == 0, err
    assert receipt["git"] == "init"
    assert (root / ".git").is_dir()
    assert (root / ".gitignore").read_text() == "data/\n__pycache__/\n"
    assert git.head(root) is not None and git.dirty(root, ["."]) == frozenset()
    assert git.log_commits(root, ["limits.json"])[0].hash == receipt["commit"]
    code, receipt, _ = run(["start", str(root / "inner")])
    assert code == 0
    assert receipt["git"] == "inside"
    assert not (root / "inner" / ".git").exists()


def test_a_verb_needing_a_commit_refuses_outside_a_repository(book, run):
    (book.parent / ".git").rename(book.parent / "moved.git")
    code, _, err = run(["check", str(book)])
    assert code == 1 and "book must be a git repository" in err


def test_absent_status_reads_research_and_a_foreign_word_stays_unknown(book, run):
    (book / "strategies" / "quiet").mkdir()
    (book / "strategies" / "empty").mkdir()
    (book / "strategies" / "empty" / "status").write_text("\n")
    (book / "strategies" / "odd").mkdir()
    (book / "strategies" / "odd" / "status").write_text("testing\n")
    _, view, _ = run(["check", str(book)])
    assert {"quiet", "empty"} <= set(view["strategies"]["research"])
    assert view["strategies"]["unknown"] == [{"strategy": "odd", "status": "testing"}]
    _, quiet, _ = run(["check", str(book), "quiet"])
    assert quiet["status"] == "research"
    assert not [b for b in quiet["blockers"] if b.startswith("status")]
    _, odd, _ = run(["check", str(book), "odd"])
    assert odd["status"] == "testing"
