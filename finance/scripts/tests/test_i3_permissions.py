"""Invariant 3: the ledger is append-only; `record` is the only writer, so a
write to `ledger/` by any other path fails on permissions."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from btm_finance import store
from btm_finance.store import append_ledger

from btm_corekit import CommandError

pytestmark = pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="root ignores mode bits; run as the book's own user",
)


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


def test_another_path_cannot_write_and_record_still_appends(book, run, make_hypothesis):
    path = book / "ledger" / "hypotheses.jsonl"
    with pytest.raises(PermissionError):
        path.open("a")
    with pytest.raises(PermissionError):
        (book / "ledger" / "planted.jsonl").open("w")
    with pytest.raises(PermissionError):
        (book / "ledger" / "runs" / "planted.jsonl").open("w")
    record_two(book, run, make_hypothesis)
    assert len(path.read_bytes().splitlines()) == 3  # baseline, then two
    assert path.stat().st_mode & 0o777 == 0o444
    assert (book / "ledger").stat().st_mode & 0o777 == 0o555


def test_a_line_is_id_ts_then_the_record(book, run, make_hypothesis):
    lines = record_two(book, run, make_hypothesis).read_bytes().splitlines()
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
    assert path.stat().st_mode & 0o777 == 0o444


def test_the_pad_stays_writable(book):
    pad = book / "ledger" / "pad"
    assert pad.stat().st_mode & 0o777 == 0o755


def test_record_refuses_to_append_after_a_cut_line(book, run, make_hypothesis):
    path = record_two(book, run, make_hypothesis)
    path.chmod(0o644)  # the operator's hand, outside record
    path.write_bytes(path.read_bytes()[:-1])
    path.chmod(0o444)
    before = path.read_bytes()
    batch = {"hypotheses": [make_hypothesis(["third", "idea"])]}
    code, _, err = run(["record", str(book), "--batch:stdin"], json.dumps(batch))
    assert code == 1
    assert "cut line" in err and "operator repairs" in err
    assert path.read_bytes() == before
