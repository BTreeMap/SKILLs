"""Session filesystem: where a ledger lives, how it is read, appended, described."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    SessionStore,
    append_jsonl,
    now_iso,
    read_jsonl,
    write_atomic,
)
from btm_ponder.ledger import replay
from btm_ponder.state import Open
from btm_ponder.views import counts_of, yield_table

STORE = SessionStore(
    "ponder", marker="ledger.jsonl", hint="open with --question creates one"
)


def ledger_path(directory: Path) -> Path:
    return directory / STORE.marker


def read_events(directory: Path) -> list[dict[str, Any]]:
    path = ledger_path(directory)
    if not path.exists():
        raise CommandError(f"no session at {directory}; open with --question creates")
    return read_jsonl(path)


def append_events(directory: Path, admitted: list[dict[str, Any]]) -> None:
    stamp = now_iso()
    append_jsonl(ledger_path(directory), [{"t": stamp, **raw} for raw in admitted])


def read_meta(directory: Path) -> dict[str, Any]:
    path = directory / "session.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def write_meta(directory: Path, meta: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    write_atomic(
        directory / "session.json", json.dumps(meta, indent=2, ensure_ascii=False)
    )
    ledger_path(directory).touch()


def orient(directory: Path) -> dict[str, Any]:
    """The re-orientation payload: everything a resumed agent needs first."""
    events = read_events(directory)
    ledger = replay(events)
    return {
        "session": directory.name,
        "question": read_meta(directory).get("question"),
        "focus": read_meta(directory).get("focus"),
        "counts": counts_of(ledger),
        "open": [
            {"id": leaf_id, "q": leaf.question}
            for leaf_id, leaf in ledger.leaves.items()
            if isinstance(leaf.state, Open)
        ],
        "swept": ledger.swept,
        "yield": yield_table(events),
    }
