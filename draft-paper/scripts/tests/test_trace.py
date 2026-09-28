"""Verification of the run trace, good and broken."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from btm_corekit import CommandError
from btm_draft_paper.cli import main
from btm_draft_paper.trace import verify

EVENTS = ["run-started", "stage-entered", "decision"]


def make_records(n: int = 3, **overrides: Any) -> list[dict[str, Any]]:
    return [
        {
            "seq": i + 1,
            "t": "2026-09-28T07:00:00+00:00",
            "run_id": "demo",
            "event": EVENTS[i % len(EVENTS)],
            "detail": {},
            **overrides,
        }
        for i in range(n)
    ]


def write_trace(directory: Path, text: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "TRACE.jsonl").write_text(text, encoding="utf-8")
    return directory


def write_records(directory: Path, records: list[dict[str, Any]]) -> Path:
    return write_trace(
        directory, "".join(json.dumps(record) + "\n" for record in records)
    )


def test_verify_good(tmp_path: Path) -> None:
    run_dir = write_records(tmp_path / "run", make_records(3))
    assert verify(run_dir) == {"run_id": "demo", "events": 3}


def test_verify_blank_lines_ignored(tmp_path: Path) -> None:
    records = make_records(2)
    text = json.dumps(records[0]) + "\n\n" + json.dumps(records[1]) + "\n"
    run_dir = write_trace(tmp_path / "run", text)
    assert verify(run_dir) == {"run_id": "demo", "events": 2}


def test_verify_seq_gap(tmp_path: Path) -> None:
    records = make_records(3)
    records[2]["seq"] = 4
    run_dir = write_records(tmp_path / "run", records)
    with pytest.raises(CommandError, match="seq"):
        verify(run_dir)


def test_verify_unknown_event(tmp_path: Path) -> None:
    run_dir = write_records(tmp_path / "run", make_records(2, event="nap"))
    with pytest.raises(CommandError, match=r"line 1: event"):
        verify(run_dir)


def test_verify_missing_field(tmp_path: Path) -> None:
    records = make_records(1)
    del records[0]["detail"]
    run_dir = write_records(tmp_path / "run", records)
    with pytest.raises(CommandError, match=r"line 1: detail"):
        verify(run_dir)


def test_verify_run_id_change(tmp_path: Path) -> None:
    records = make_records(2)
    records[1]["run_id"] = "other"
    run_dir = write_records(tmp_path / "run", records)
    with pytest.raises(CommandError, match="run_id changed"):
        verify(run_dir)


def test_verify_invalid_json(tmp_path: Path) -> None:
    run_dir = write_trace(tmp_path / "run", "{not json}\n")
    with pytest.raises(CommandError, match="invalid JSON"):
        verify(run_dir)


def test_verify_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CommandError, match="no trace"):
        verify(tmp_path / "absent")


def test_verify_empty(tmp_path: Path) -> None:
    run_dir = write_trace(tmp_path / "run", "\n")
    with pytest.raises(CommandError, match="no events"):
        verify(run_dir)


def test_verify_bool_seq_rejected(tmp_path: Path) -> None:
    records = make_records(1)
    records[0]["seq"] = True
    run_dir = write_records(tmp_path / "run", records)
    with pytest.raises(CommandError, match="line 1"):
        verify(run_dir)


def test_verify_extra_field_rejected(tmp_path: Path) -> None:
    records = make_records(1)
    records[0]["bogus"] = "typo"
    run_dir = write_records(tmp_path / "run", records)
    with pytest.raises(CommandError, match="line 1"):
        verify(run_dir)


def test_verify_non_object_json(tmp_path: Path) -> None:
    run_dir = write_trace(tmp_path / "run", "[1, 2]\n")
    with pytest.raises(CommandError, match="not a JSON object"):
        verify(run_dir)


def test_verify_bad_timestamp(tmp_path: Path) -> None:
    run_dir = write_records(tmp_path / "run", make_records(1, t="yesterday"))
    with pytest.raises(CommandError, match="line 1"):
        verify(run_dir)


def test_cli_verify_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = write_records(tmp_path / "run", make_records(2))
    assert main(["trace", "verify", str(run_dir)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary == {"run_id": "demo", "events": 2}


def test_cli_verify_broken(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    records = make_records(2)
    records[1]["seq"] = 9
    run_dir = write_records(tmp_path / "run", records)
    assert main(["trace", "verify", str(run_dir)]) == 1
    assert "seq" in capsys.readouterr().err
