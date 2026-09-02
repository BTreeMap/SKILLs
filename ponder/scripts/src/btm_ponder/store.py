"""Session filesystem: where a ledger lives, how it is read, appended, described."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from btm_corekit import EventLog, SessionStore
from btm_ponder.ledger import replay
from btm_ponder.state import Open
from btm_ponder.views import counts_of, yield_table

STORE = SessionStore("ponder", marker="session.json", hint="run init first")
LEDGER = "ledger.jsonl"


def event_log(directory: Path) -> EventLog:
    return EventLog(directory / LEDGER, STORE.hint)


def read_events(directory: Path) -> list[dict[str, Any]]:
    return event_log(directory).read()


def read_meta(directory: Path) -> dict[str, Any]:
    return STORE.read_meta(directory)


def write_meta(directory: Path, meta: dict[str, Any]) -> None:
    STORE.write_meta(directory, meta)
    event_log(directory).touch()


def orient(directory: Path) -> dict[str, Any]:
    """The status payload: everything a resumed agent needs first."""
    events = read_events(directory)
    ledger = replay(events)
    meta = read_meta(directory)
    attached = Counter(source.leaf for source in ledger.sources.values())
    return {
        "session": directory.name,
        "question": meta.get("question"),
        "focus": meta.get("focus"),
        "mode": meta.get("mode", "full"),
        "counts": counts_of(ledger),
        "sources": len(ledger.sources),
        "swept": ledger.swept,
        "open": [
            {"id": leaf_id, "q": leaf.question, "sources": attached[leaf_id]}
            for leaf_id, leaf in ledger.leaves.items()
            if isinstance(leaf.state, Open)
        ],
        "last_checkpoint": next(
            (
                event.get("label")
                for event in reversed(events)
                if event.get("e") == "checkpoint"
            ),
            None,
        ),
        "yield": yield_table(events),
    }
