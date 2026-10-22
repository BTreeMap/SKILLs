"""`measure --repeat`: a run reproduces from its own inputs and writes nothing;
code read from its recorded blob ids and compared by AST against the
working tree, raw data, or a peer series that moved is refused by name."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from btm_finance import git
from btm_finance.repeat import Rule, compare

SOURCE = Path(__file__).resolve().parents[1] / "src" / "btm_finance"


def snapshot(book: Path) -> dict[str, bytes]:
    return {
        path.relative_to(book).as_posix(): path.read_bytes()
        for path in sorted(book.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def measured(synthetic, run):
    """A book with two baseline runs; the second lists the first as peer."""
    book = synthetic(seed=7)
    ids = []
    for _ in range(2):
        code, document, err = run(["measure", str(book), "baseline"])
        assert code == 0, err
        ids.append(document["run_id"])
    return book, ids


def flip(path: Path) -> None:
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    path.write_bytes(bytes(data))


def test_a_run_reproduces_and_writes_nothing(measured, run):
    book, (_, second) = measured
    before = snapshot(book)
    code, document, err = run(["measure", str(book), "baseline", "--repeat", second])
    assert code == 0, err
    assert (document["reproduced"], document["diffs"]) == (True, [])
    assert document["compared"] > 20
    assert snapshot(book) == before


def test_a_moved_engine_commit_is_advisory(measured, run, monkeypatch):
    book, (first, _) = measured
    monkeypatch.setattr(git, "skill_commit", lambda: "f" * 40)
    code, document, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 0, err
    assert document["reproduced"] is True
    [note] = document["advisories"]
    assert note.startswith("btm_finance ") and note.endswith(" -> " + "f" * 40)


def test_a_run_measured_on_a_branch_repeats_after_rebase(
    synthetic, run, commit, rebase, git_in
):
    book = synthetic(seed=7)
    git_in(book, "switch", "-q", "-c", "agent/tilt")
    signal = book / "strategies" / "baseline" / "signal.py"
    signal.write_text(signal.read_text() + "\nEXTRA = 1\n")
    before = commit(book, "strategies/baseline", subject="feat: tilt baseline")
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    rebase(book, "agent/tilt")
    assert git.head(book) != before
    code, again, err = run(
        ["measure", str(book), "baseline", "--repeat", document["run_id"]]
    )
    assert code == 0, err
    assert again["reproduced"] is True


def test_an_edited_config_is_refused_by_name(measured, run):
    book, (first, _) = measured
    path = book / "strategies" / "baseline" / "config.json"
    config = json.loads(path.read_text())
    config["params"]["vol_days"] = 126
    path.write_text(json.dumps(config))
    code, _, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 1
    assert "code moved: strategies/baseline/config.json" in err
    assert "signal.py" not in err


def test_a_reformat_commit_reproduces_and_a_semantic_commit_refuses(
    measured, run, commit
):
    book, (first, _) = measured
    signal = book / "strategies" / "baseline" / "signal.py"
    signal.write_text("# reformatted\n\n" + signal.read_text() + "\n\n# end\n")
    commit(book, "strategies/baseline", subject="style: reformat baseline")
    code, document, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 0, err
    assert document["reproduced"] is True
    signal.write_text(signal.read_text() + "\nEXTRA = 1\n")
    commit(book, "strategies/baseline", subject="feat: change baseline")
    code, _, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 1
    assert "code moved: strategies/baseline/signal.py" in err


def test_a_reformat_of_either_file_reproduces(measured, run):
    book, (first, _) = measured
    folder = book / "strategies" / "baseline"
    config = folder / "config.json"
    parsed = json.loads(config.read_text())
    config.write_text(json.dumps(dict(reversed(parsed.items())), indent=7))
    signal = folder / "signal.py"
    spaced = signal.read_text().replace("\ndef ", "\n\n\ndef ")
    signal.write_text("# reformatted\n\n\n" + spaced + "\n# end\n")
    code, document, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 0, err
    assert document["reproduced"] is True


def test_a_code_edit_is_refused_by_name(measured, run):
    book, (first, _) = measured
    signal = book / "strategies" / "baseline" / "signal.py"
    signal.write_text(signal.read_text() + "\nEXTRA = 1\n")
    code, _, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 1
    assert "code moved: strategies/baseline/signal.py" in err


def test_a_corrupted_peer_series_is_refused(measured, run):
    book, (first, second) = measured
    flip(book / "data" / "returns" / f"{first}.parquet")
    before = snapshot(book)
    code, _, err = run(["measure", str(book), "baseline", "--repeat", second])
    assert code == 1
    assert f"peer {first}: returns file changed" in err
    assert snapshot(book) == before  # no incident either: the repeat writes nothing


def test_a_changed_raw_file_is_refused_by_name(measured, run):
    book, (first, _) = measured
    (raw,) = sorted((book / "data" / "raw" / "csv").glob("*.bars.parquet"))
    flip(raw)
    code, _, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 1
    assert f"{raw.relative_to(book).as_posix()} changed" in err


def test_the_comparison_is_absolute_to_one_then_relative():
    count, diffs = compare(
        {"a": 0.5, "b": 200.0, "c": None, "d": [1, 2]},
        {"a": 0.50009, "b": 200.019, "c": None, "d": [1, 2]},
        1e-4,
    )
    assert (count, diffs) == (5, [])
    _, diffs = compare(
        {"a": 0.5, "b": 200.0, "c": None}, {"a": 0.5002, "b": 200.03, "c": 0.0}, 1e-4
    )
    assert [(d.path, d.rule) for d in diffs] == [
        ("scorecard.a", Rule.ABSOLUTE),
        ("scorecard.b", Rule.RELATIVE),
        ("scorecard.c", Rule.EXACT),
    ]


def test_a_lib_module_is_compared_beside_signal(synthetic, run, commit):
    book = synthetic(seed=7)
    module = book / "lib" / "tilt.py"
    module.write_text("def scale(weight):\n    return weight\n")
    signal = book / "strategies" / "baseline" / "signal.py"
    signal.write_text("import lib.tilt\n" + signal.read_text())
    commit(book, "lib", "strategies/baseline")
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    run_id = document["run_id"]
    line = json.loads((book / "ledger" / "runs.jsonl").read_text().splitlines()[-1])
    assert set(line["code_paths"]) >= {"lib/__init__.py", "lib/tilt.py"}

    module.write_text("# spaced\n\n\ndef scale(weight):\n\n    return weight\n")
    code, document, err = run(["measure", str(book), "baseline", "--repeat", run_id])
    assert code == 0, err
    assert document["reproduced"] is True

    module.write_text("def scale(weight):\n    return 2 * weight\n")
    code, _, err = run(["measure", str(book), "baseline", "--repeat", run_id])
    assert code == 1
    assert "code moved: lib/tilt.py" in err
    assert "signal.py" not in err.split("code moved:")[1]


def test_no_tracked_file_is_digested_outside_the_data_manifest():
    """Git points at tracked content; sha256 guards only untracked `data/`,
    through `data/manifest.json` entries."""
    hits = [
        (path.relative_to(SOURCE).as_posix(), line)
        for path in SOURCE.rglob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if "sha256" in line
    ]
    assert {name for name, _ in hits} == {"data/raw.py", "cli.py"}
    for name, line in hits:
        if name == "cli.py":
            assert "sha256_of" in line or "e.sha256" in line, line
