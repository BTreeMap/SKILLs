"""The pad: free working memory beside a skill's gated stores.

jot admits anything and loses nothing. The body is stored verbatim under
its own key, so no body field can collide with the script-stamped envelope
(id, time), and every byte comes back through recall. Rigor lives behind
the gated verbs; the only failure here is an unreadable filter argument.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from btm_corekit.clock import now_iso
from btm_corekit.errors import CommandError
from btm_corekit.fsio import append_jsonl, read_jsonl

SCRATCH = "scratch.jsonl"
PAD_SOFT_CAP = 500  # advisory line, never a refusal

_ENTRY_ID = re.compile(r"j(\d+)")


def pad_entries(directory: Path) -> list[dict[str, Any]]:
    """Rows the pad holds; a line appended by hand reads as a bare body.

    Positional ids match jot's count-based minting, so the two write paths
    never collide.
    """
    path = directory / SCRATCH
    if not path.exists():
        return []
    try:
        rows = read_jsonl(path)
    except json.JSONDecodeError as err:
        raise CommandError(f"{path} holds a line that is not JSON: {err}") from err
    return [_enveloped(number, row) for number, row in enumerate(rows, start=1)]


def _enveloped(number: int, row: Any) -> dict[str, Any]:
    if isinstance(row, dict) and isinstance(row.get("body"), dict):
        return row
    body = row if isinstance(row, dict) else {"text": str(row)}
    return {"j": f"j{number}", "t": "", "body": body}


def pad_ids(directory: Path) -> set[str]:
    return {entry["j"] for entry in pad_entries(directory)}


def _line_count(path: Path) -> int:
    """Non-empty lines, matching read_jsonl's filter; no JSON parse needed."""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def jot(directory: Path, body: Mapping[str, Any]) -> dict[str, Any]:
    """Append one entry; the receipt echoes the minted id."""
    directory.mkdir(parents=True, exist_ok=True)
    count = _line_count(directory / SCRATCH) + 1
    record = {"j": f"j{count}", "t": now_iso(), "body": dict(body)}
    append_jsonl(directory / SCRATCH, [record])
    receipt: dict[str, Any] = {"jotted": record["j"], "entries": count}
    if count > PAD_SOFT_CAP:
        receipt["advisory"] = (
            f"pad holds {count} entries; recall filters keep reads cheap"
        )
    return receipt


def pad_body(raw: str, as_text: bool = False) -> tuple[dict[str, Any], str | None]:
    """Anything becomes a body: a JSON object as itself, all else wrapped as
    text with an advisory. The pad path never rejects content."""
    if not as_text:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(parsed, dict):
                return parsed, None
        return {"text": raw}, 'stored as {"text": ...}: the entry is not a JSON object'
    return {"text": raw}, None


def _entry_number(entry_id: str) -> int:
    if match := _ENTRY_ID.fullmatch(entry_id):
        return int(match.group(1))
    raise CommandError(f"pad ids look like j12; got {entry_id!r}")


def recall(
    directory: Path,
    *,
    kind: str | None = None,
    match: str | None = None,
    since: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Filtered slice of the pad, oldest first; O(entries) per call."""
    entries = pad_entries(directory)
    total = len(entries)
    if since is not None:
        floor = _entry_number(since)
        entries = [e for e in entries if _entry_number(e["j"]) > floor]
    if kind is not None:
        entries = [e for e in entries if e["body"].get("kind") == kind]
    if match is not None:
        try:
            pattern = re.compile(match, re.IGNORECASE)
        except re.error as err:
            raise CommandError(f"unreadable --match pattern: {err}") from err
        entries = [
            e
            for e in entries
            if pattern.search(json.dumps(e["body"], ensure_ascii=False))
        ]
    if limit is not None:
        entries = entries[-limit:]
    return {"total": total, "shown": len(entries), "entries": entries}
