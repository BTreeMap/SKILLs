"""The chained ledger, pure: line making, the chain audit, and replay.

Every line is `id`, `ts`, `prev`, then the record; `prev` is the sha256 hex
of the previous line's exact bytes (newline excluded), null on line one.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

ENVELOPE = ("id", "ts", "prev")
Row = dict[str, Any]
Numbered = tuple[int, Row]


class Kind(StrEnum):
    """One JSONL file per kind under `ledger/`."""

    HYPOTHESIS = "hypothesis"
    CRITIQUE = "critique"
    DECISION = "decision"
    FILL = "fill"
    RUN = "run"
    INCIDENT = "incident"

    @property
    def file(self) -> str:
        match self:
            case Kind.HYPOTHESIS:
                return "hypotheses.jsonl"
            case Kind.CRITIQUE:
                return "critiques.jsonl"
            case Kind.DECISION:
                return "decisions.jsonl"
            case Kind.FILL:
                return "fills.jsonl"
            case Kind.RUN:
                return "runs.jsonl"
            case Kind.INCIDENT:
                return "incidents.jsonl"


def line_digest(line: bytes) -> str:
    return hashlib.sha256(line).hexdigest()


def last_line(data: bytes) -> bytes | None:
    """The final line's bytes, newline excluded; None for an empty file."""
    body = data.removesuffix(b"\n")
    return body.rpartition(b"\n")[2] if body else None


def chained(last: bytes | None, records: Iterable[Mapping[str, Any]]) -> list[bytes]:
    """Each record as one line linked to the line before it. Envelope keys in
    a record body are dropped: the chain owns them."""
    prev = None if last is None else line_digest(last)
    lines: list[bytes] = []
    for record in records:
        body = {key: value for key, value in record.items() if key not in ENVELOPE}
        row = {"id": record["id"], "ts": record["ts"], "prev": prev, **body}
        line = json.dumps(row, ensure_ascii=False).encode("utf-8")
        lines.append(line)
        prev = line_digest(line)
    return lines


@dataclass(frozen=True, slots=True)
class Break:
    """One place a chain or a reference fails, by file and 1-based line."""

    file: str
    line: int
    problem: str

    def view(self) -> dict[str, Any]:
        return {"file": self.file, "line": self.line, "problem": self.problem}


def split_lines(data: bytes) -> tuple[list[bytes], bool]:
    """Lines without their newlines, and whether the last one was terminated."""
    if not data:
        return [], True
    lines = data.split(b"\n")
    terminated = lines[-1] == b""
    if terminated:
        lines.pop()
    return lines, terminated


def audit(name: str, data: bytes) -> list[Break]:
    """Every chain break in one file, never repaired. O(bytes): one split and
    one sha256 per line, Python iterating per line, never per byte."""
    lines, terminated = split_lines(data)
    breaks: list[Break] = []
    previous: bytes | None = None
    for number, line in enumerate(lines, start=1):
        row = decode(line)
        if row is None:
            breaks.append(Break(name, number, "line is not a JSON object"))
        else:
            expected = None if previous is None else line_digest(previous)
            if row.get("prev") != expected:
                breaks.append(Break(name, number, mismatch(number)))
        previous = line
    if not terminated:
        breaks.append(
            Break(name, len(lines), "last line has no newline: a write was cut short")
        )
    return breaks


def mismatch(number: int) -> str:
    if number == 1:
        return "prev must be null on line 1: a line before it was removed"
    return (
        f"prev is not the sha256 of line {number - 1}: line {number - 1} "
        f"or line {number} was edited, or a line between them removed"
    )


def decode(line: bytes) -> Row | None:
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row if isinstance(row, dict) else None


def rows_of(data: bytes) -> list[Numbered]:
    """Every decodable row with its 1-based line; `audit` names the rest."""
    lines, _ = split_lines(data)
    decoded = ((number, decode(line)) for number, line in enumerate(lines, start=1))
    return [(number, row) for number, row in decoded if row is not None]


def current(rows: Sequence[Numbered]) -> list[Row]:
    """The derived view: a line carrying `supersedes: <id>` replaces that id."""
    replaced = {
        row["supersedes"] for _, row in rows if isinstance(row.get("supersedes"), str)
    }
    return [row for _, row in rows if row.get("id") not in replaced]


def dangling(name: str, rows: Sequence[Numbered]) -> list[Break]:
    """Every `supersedes` naming no id in its own file."""
    ids = {row.get("id") for _, row in rows}
    return [
        Break(name, number, f"supersedes '{row['supersedes']}', which no line holds")
        for number, row in rows
        if "supersedes" in row and row["supersedes"] not in ids
    ]
