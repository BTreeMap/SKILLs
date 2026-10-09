"""Session filesystem: where a ledger lives, how it is read, appended, described."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from btm_corekit import EventLog, NonEmpty, SessionStore, Tagged, dump
from btm_ponder.ledger import replay
from btm_ponder.state import Ledger, Level, Open
from btm_ponder.views import counts_of, yield_table

STORE = SessionStore("ponder", marker="session.json", hint="run start first")
LEDGER = "ledger.jsonl"


class SessionMeta(Tagged):
    """What one session is about, fixed at start."""

    question: NonEmpty
    focus: str | None = None
    level: Level = Level.FULL
    created: str = ""


def next_step(ledger: Ledger, open_leaves: int) -> str:
    """The cheapest legal next action, derived from live ledger state.

    Advisory only: how many cycles a question deserves is judgment. What the
    script owes is the arithmetic over leaves, sources, and the scan."""
    if not ledger.leaves:
        return "register the frame leaves for this question"
    if open_leaves:
        return f"close {open_leaves} open leaves: add sources, then a close each"
    if not ledger.scanned:
        return "run the rival scan, then record it"
    return "draft from check output"


def orient(directory: Path) -> dict[str, Any]:
    """The status payload: everything a continuing agent needs first."""
    events = EventLog(directory / LEDGER).read()
    ledger = replay(events)
    meta = STORE.read_meta(directory, SessionMeta)
    attached = Counter(source.leaf for source in ledger.sources.values())
    open_leaves = [
        {"id": leaf_id, "q": leaf.question, "sources": attached[leaf_id]}
        for leaf_id, leaf in ledger.leaves.items()
        if isinstance(leaf.status, Open)
    ]
    return {
        "session": directory.name,
        "question": meta.question,
        "focus": meta.focus,
        "project": meta.project,
        "connections": [dump(connection) for connection in meta.connections],
        "level": meta.level,
        "counts": counts_of(ledger),
        "sources": len(ledger.sources),
        "scanned": ledger.scanned,
        "open": open_leaves,
        "last_checkpoint": next(
            (
                event.get("label")
                for event in reversed(events)
                if event.get("e") == "checkpoint"
            ),
            None,
        ),
        "yield": yield_table(events),
        "next": next_step(ledger, len(open_leaves)),
    }
