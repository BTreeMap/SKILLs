"""Session filesystem: where a ledger lives, how it is read, appended, described."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from btm_corekit import EventLog, Model, NonEmpty, SessionStore
from btm_ponder.ledger import replay
from btm_ponder.state import Ledger, Mode, Open
from btm_ponder.views import counts_of, yield_table

STORE = SessionStore("ponder", marker="session.json", hint="run init first")
LEDGER = "ledger.jsonl"


class SessionMeta(Model):
    """What one session is about, fixed at init."""

    question: NonEmpty
    focus: str | None = None
    mode: Mode = Mode.FULL
    created: str = ""


def event_log(directory: Path) -> EventLog:
    return EventLog(directory / LEDGER, STORE.hint)


def read_events(directory: Path) -> list[dict[str, Any]]:
    return event_log(directory).read()


def read_meta(directory: Path) -> SessionMeta:
    return STORE.read_meta(directory, SessionMeta)


def write_meta(directory: Path, meta: SessionMeta) -> None:
    STORE.write_meta(directory, meta)
    event_log(directory).touch()


def next_step(ledger: Ledger, open_leaves: int) -> str:
    """The cheapest legal next action, derived from live ledger state.

    Advisory only: how many rounds a question deserves is judgment. What the
    script owes is the arithmetic over leaves, sources, and the sweep."""
    if not ledger.leaves:
        return "register the frame leaves for this question"
    if open_leaves:
        return f"close {open_leaves} open leaves: add sources, then a close each"
    if not ledger.swept:
        return "run the rival sweep, then note it"
    return "draft from check output"


def orient(directory: Path) -> dict[str, Any]:
    """The status payload: everything a resumed agent needs first."""
    events = read_events(directory)
    ledger = replay(events)
    meta = read_meta(directory)
    attached = Counter(source.leaf for source in ledger.sources.values())
    open_leaves = [
        {"id": leaf_id, "q": leaf.question, "sources": attached[leaf_id]}
        for leaf_id, leaf in ledger.leaves.items()
        if isinstance(leaf.state, Open)
    ]
    return {
        "session": directory.name,
        "question": meta.question,
        "focus": meta.focus,
        "mode": meta.mode,
        "counts": counts_of(ledger),
        "sources": len(ledger.sources),
        "swept": ledger.swept,
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
