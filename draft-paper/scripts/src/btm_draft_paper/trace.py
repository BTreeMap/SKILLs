"""Verification for the append-only run trace, TRACE.jsonl.

The log type, the event cap, the record decoder, and the failure type come
from the kernel; lines are read here so each defect names its line."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, StrictInt

from btm_corekit import MAX_EVENTS, CommandError, EventLog, Model, parse_model

TRACE_NAME = "TRACE.jsonl"

Seq = Annotated[StrictInt, Field(gt=0)]
"""A 1-based position: a real integer, never a bool, never zero."""


class EventName(StrEnum):
    """The closed event vocabulary; the decoder rejects anything else."""

    RUN_STARTED = "run-started"
    STAGE_ENTERED = "stage-entered"
    STAGE_EXITED = "stage-exited"
    GATE_REQUESTED = "gate-requested"
    GATE_APPROVED = "gate-approved"
    GATE_REJECTED = "gate-rejected"
    EXPERIMENT_REGISTERED = "experiment-registered"
    EXPERIMENT_COMPLETED = "experiment-completed"
    CLAIM_ADDED = "claim-added"
    CLAIM_DROPPED = "claim-dropped"
    DECISION = "decision"


class Event(Model):
    """One decoded trace line. The kernel's Model is frozen and forbids
    extra fields, so a typo'd key is a located error, not silent drift."""

    seq: Seq
    t: datetime
    run_id: str
    event: EventName
    detail: dict[str, Any]


def trace_log(directory: Path) -> EventLog:
    """The run's trace log, with a hint naming the draft-paper run."""
    return EventLog(directory / TRACE_NAME, "start a draft-paper run first")


def verify(directory: Path) -> dict[str, Any]:
    """Check a run's trace; raise CommandError naming the first defect."""
    log = trace_log(directory)
    if not log.exists():
        raise CommandError(f"no trace at {log.path}: start a run first")
    if log.count() > MAX_EVENTS:
        raise CommandError(
            f"trace holds {log.count()} events, over the {MAX_EVENTS} cap"
        )
    lines = log.path.read_text(encoding="utf-8").splitlines()
    numbered = [(number, line) for number, line in enumerate(lines, 1) if line.strip()]
    events = [(number, _decode(number, line)) for number, line in numbered]
    return _check(log.path, events)


def _decode(number: int, line: str) -> Event:
    """Parse one line: JSON shape first, then the record decoder."""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        raise CommandError(f"line {number}: invalid JSON") from None
    if not isinstance(raw, dict):
        raise CommandError(f"line {number}: not a JSON object")
    return parse_model(Event, raw, f"line {number}")


def _check(path: Path, events: list[tuple[int, Event]]) -> dict[str, Any]:
    """Pure: ordering and identity rules over decoded events."""
    if not events:
        raise CommandError(f"trace at {path} holds no events")
    run_id = events[0][1].run_id
    for position, (number, event) in enumerate(events, 1):
        if event.seq != position:
            raise CommandError(
                f"line {number}: seq is {event.seq}, expected {position}"
            )
        if event.run_id != run_id:
            raise CommandError(
                f"line {number}: run_id changed from {run_id!r} to {event.run_id!r}"
            )
    return {"run_id": run_id, "events": len(events)}
