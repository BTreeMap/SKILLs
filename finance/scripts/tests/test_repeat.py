"""`measure --repeat`: a run reproduces from its own inputs and writes nothing;
code whose AST digest moved from the recorded `code_files`, raw data, or a
peer series that moved is refused by name."""

from __future__ import annotations

import json
from pathlib import Path

import btm_finance
import pytest
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


def test_a_moved_engine_version_is_advisory(measured, run, monkeypatch):
    book, (first, _) = measured
    monkeypatch.setattr(btm_finance, "__version__", "9.9.9")
    code, document, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 0, err
    assert document["reproduced"] is True
    [note] = document["advisories"]
    assert note.startswith("btm_finance ") and note.endswith(" -> 9.9.9")


def test_a_line_without_a_code_hash_is_refused(measured, run):
    book, (first, _) = measured
    path = book / "ledger" / "runs.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:  # an older line: blob ids, a library map
        del row["code_hash"], row["code_files"]
        row["code_objects"] = {"strategies/baseline/signal.py": "0" * 40}
        row["engine"] = {"btm_finance": row["engine"], "numpy": "2.0"}
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    code, _, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 1
    assert "run line predates code hashes" in err


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


def test_a_reformat_reproduces_and_a_semantic_edit_refuses(measured, run):
    book, (first, _) = measured
    signal = book / "strategies" / "baseline" / "signal.py"
    signal.write_text("# reformatted\n\n" + signal.read_text() + "\n\n# end\n")
    code, document, err = run(["measure", str(book), "baseline", "--repeat", first])
    assert code == 0, err
    assert document["reproduced"] is True
    signal.write_text(signal.read_text() + "\nEXTRA = 1\n")
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


def test_a_lib_module_is_compared_beside_signal(synthetic, run):
    book = synthetic(seed=7)
    module = book / "lib" / "tilt.py"
    module.write_text("def scale(weight):\n    return weight\n")
    signal = book / "strategies" / "baseline" / "signal.py"
    signal.write_text("import lib.tilt\n" + signal.read_text())
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    run_id = document["run_id"]
    line = json.loads((book / "ledger" / "runs.jsonl").read_text().splitlines()[-1])
    assert set(line["code_files"]) >= {"lib/__init__.py", "lib/tilt.py"}

    module.write_text("# spaced\n\n\ndef scale(weight):\n\n    return weight\n")
    code, document, err = run(["measure", str(book), "baseline", "--repeat", run_id])
    assert code == 0, err
    assert document["reproduced"] is True

    module.write_text("def scale(weight):\n    return 2 * weight\n")
    code, _, err = run(["measure", str(book), "baseline", "--repeat", run_id])
    assert code == 1
    assert "code moved: lib/tilt.py" in err
    assert "signal.py" not in err.split("code moved:")[1]


def test_sha256_lives_in_the_manifest_snapshot_and_code_hash_only():
    """`data/raw.py` digests the store; `repeat.py` digests code; `cli.py`
    only reads those digests; git runs only in `scaffold.py` (init) and
    `delegation.py` (brief blob ids and history)."""
    hits = [
        (path.relative_to(SOURCE).as_posix(), line)
        for path in SOURCE.rglob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if "sha256" in line
    ]
    assert {name for name, _ in hits} == {"data/raw.py", "cli.py", "repeat.py"}
    for name, line in hits:
        if name == "cli.py":
            assert "sha256_of" in line or "e.sha256" in line, line
    callers = {
        path.relative_to(SOURCE).as_posix()
        for path in SOURCE.rglob("*.py")
        if '"git"' in path.read_text(encoding="utf-8")
    }
    assert callers == {"scaffold.py", "delegation.py"}
