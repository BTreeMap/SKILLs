"""The ledger, pure: line making and replay. Every line is `id`, `ts`, then
the record; a correction is a new line carrying `supersedes`."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from typing import Any

ENVELOPE = ("id", "ts")
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
    REGIME = "regime"

    @property
    def file(self) -> str:
        match self:
            case Kind.HYPOTHESIS:
                stem = "hypotheses"
            case (
                Kind.CRITIQUE
                | Kind.DECISION
                | Kind.FILL
                | Kind.RUN
                | Kind.INCIDENT
                | Kind.REGIME
            ):
                stem = f"{self.value}s"
        return f"{stem}.jsonl"


def lines_of(records: Iterable[Mapping[str, Any]]) -> list[bytes]:
    """Each record as one line: `id`, `ts`, then the body. Envelope keys in a
    record body are dropped: the writer owns them."""
    lines: list[bytes] = []
    for record in records:
        body = {key: value for key, value in record.items() if key not in ENVELOPE}
        row = {"id": record["id"], "ts": record["ts"], **body}
        lines.append(json.dumps(row, ensure_ascii=False).encode("utf-8"))
    return lines


def split_lines(data: bytes) -> list[bytes]:
    """Lines without their newlines; an unterminated last line is kept."""
    return data.removesuffix(b"\n").split(b"\n") if data else []


def decode(line: bytes) -> Row | None:
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row if isinstance(row, dict) else None


def rows_of(data: bytes) -> list[Numbered]:
    """Every decodable row with its 1-based line."""
    lines = split_lines(data)
    decoded = ((number, decode(line)) for number, line in enumerate(lines, start=1))
    return [(number, row) for number, row in decoded if row is not None]


def current(rows: Sequence[Numbered]) -> list[Row]:
    """The derived view: a line carrying `supersedes: <id>` replaces that id."""
    replaced = {
        row["supersedes"] for _, row in rows if isinstance(row.get("supersedes"), str)
    }
    return [row for _, row in rows if row.get("id") not in replaced]


def undecodable(name: str, data: bytes) -> list[dict[str, Any]]:
    """Every line that is not a JSON object: file, 1-based line, first 40 bytes."""
    return [
        {"file": name, "line": number, "head": line[:40].decode("utf-8", "replace")}
        for number, line in enumerate(split_lines(data), start=1)
        if decode(line) is None
    ]


def cut_line(name: str, data: bytes) -> list[dict[str, Any]]:
    """A last line without its newline: some hand other than `record` cut it."""
    if not data or data.endswith(b"\n"):
        return []
    return [{"file": name, "line": len(split_lines(data)), "problem": "cut line"}]


def dangling(
    name: str, rows: Sequence[Numbered], ids: set[Any]
) -> list[dict[str, Any]]:
    """Every `supersedes` naming no id of its kind."""
    return [
        {"file": name, "line": number, "supersedes": row["supersedes"]}
        for number, row in rows
        if "supersedes" in row and row["supersedes"] not in ids
    ]
