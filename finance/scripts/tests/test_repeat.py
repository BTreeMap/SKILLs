"""`score --repeat`: a run reproduces from its own inputs and writes nothing;
moved code, raw data, or a peer series is refused by name."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from btm_finance.repeat import Rule, compare


def snapshot(book: Path) -> dict[str, bytes]:
    return {
        path.relative_to(book).as_posix(): path.read_bytes()
        for path in sorted(book.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def scored(synthetic, run):
    """A book with two baseline runs; the second lists the first as peer."""
    book = synthetic(seed=7)
    ids = []
    for _ in range(2):
        code, document, err = run(["score", str(book), "baseline"])
        assert code == 0, err
        ids.append(document["run_id"])
    return book, ids


def flip(path: Path) -> None:
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    path.write_bytes(bytes(data))


def test_a_run_reproduces_and_writes_nothing(scored, run):
    book, (_, second) = scored
    before = snapshot(book)
    code, document, err = run(["score", str(book), "baseline", "--repeat", second])
    assert code == 0, err
    assert (document["reproduced"], document["diffs"]) == (True, [])
    assert document["compared"] > 20
    assert snapshot(book) == before


def test_an_edited_config_is_refused_by_name(scored, run):
    book, (first, _) = scored
    path = book / "strategies" / "baseline" / "config.json"
    path.write_text(json.dumps(json.loads(path.read_text()), indent=4))
    code, _, err = run(["score", str(book), "baseline", "--repeat", first])
    assert code == 1
    assert "code moved: config.json" in err
    assert "signal.py" not in err


def test_a_corrupted_peer_series_is_refused(scored, run):
    book, (first, second) = scored
    flip(book / "data" / "returns" / f"{first}.parquet")
    before = snapshot(book)
    code, _, err = run(["score", str(book), "baseline", "--repeat", second])
    assert code == 1
    assert f"peer {first}: returns file changed" in err
    assert snapshot(book) == before  # no incident either: the repeat writes nothing


def test_a_changed_raw_file_is_refused_by_name(scored, run):
    book, (first, _) = scored
    (raw,) = sorted((book / "data" / "raw" / "csv").glob("*.bars.parquet"))
    flip(raw)
    code, _, err = run(["score", str(book), "baseline", "--repeat", first])
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
