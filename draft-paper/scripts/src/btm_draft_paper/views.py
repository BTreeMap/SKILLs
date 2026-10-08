"""Derived views: the resume status, the gate summary, and the evidence
ledger. Each is computed from the replayed trace on every call."""

from __future__ import annotations

from collections import Counter
from typing import Any

from btm_corekit import pad_entries
from btm_draft_paper.run import GATE_STAGE, Gate
from btm_draft_paper.trace import (
    EVIDENCED,
    Run,
    RunState,
    Standing,
    blockers,
)

ARTIFACT = {
    Gate.PLAN: "research plan",
    Gate.LEDGER: "evidence ledger",
    Gate.DRAFT: "final draft",
}
PAD_TAIL = 3


def _pending(state: RunState) -> Gate | None:
    return next((g for g, s in state.gates.items() if s is Standing.PENDING), None)


def next_step(state: RunState) -> str:
    """The cheapest legal next action. Advisory: when a stage's work is done
    is the agent's judgment; the script owes only what the trace permits."""
    if state.closed is not None:
        return (
            f"the human rejected the {state.closed} gate and the run is closed; "
            "init a new run if they redirect the work"
        )
    if (pending := _pending(state)) is not None:
        return (
            f"present the {pending} gate from check and wait; note gate-decided "
            "with the human's reply verbatim"
        )
    if state.stage is None:
        return f"note stage-entered {state.meta.stages()[0]}"
    return _within(state, state.stage)


def _within(state: RunState, stage: int) -> str:
    gate = state.gate_at(stage)
    if gate is not None:
        match state.gates[gate]:
            case Standing.REVISE:
                return (
                    f"revise the {ARTIFACT[gate]} per the human's notes, then "
                    f"note gate-requested {gate}"
                )
            case Standing.OPEN:
                return f"finish stage {stage}, then note gate-requested {gate}"
            case Standing.APPROVED if stage < state.meta.stages()[1]:
                return f"the {gate} gate passed; note stage-entered {stage + 1}"
    if stage < state.meta.stages()[1]:
        return f"finish stage {stage}, then note stage-entered {stage + 1}"
    if gate is not None and state.gates[gate] is Standing.APPROVED:
        return "deliver per the output contract"
    return f"finish stage {stage}, then deliver per the output contract"


def status_view(run: Run) -> dict[str, Any]:
    """The cheap resume view."""
    state = run.state
    pad = pad_entries(run.directory)
    document: dict[str, Any] = {
        "session": run.directory.name,
        "verb": run.meta.verb,
        "format": run.meta.format,
        "state": run.meta.state,
        "venue": run.meta.venue,
        "model": run.meta.model,
        "stages": list(run.meta.stages()),
        "stage": state.stage,
        "gates": dict(state.gates),
        "claims": dict(Counter(claim.status for claim in state.claims.values())),
        "dropped": len(state.dropped),
        "events": state.events,
        "pad": {"total": len(pad), "tail": pad[-PAD_TAIL:]},
        "next": next_step(state),
    }
    if state.closed is not None:
        document["closed_by"] = state.closed
    return document


def _focus(state: RunState) -> Gate | None:
    """The gate in play: a pending one, else the current stage's."""
    if (pending := _pending(state)) is not None:
        return pending
    return None if state.stage is None else state.gate_at(state.stage)


def _since_last_decision(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = 0
    for index, row in enumerate(rows):
        if row.get("event") == "gate-decided":
            start = index + 1
    return [{k: v for k, v in row.items() if k != "run"} for row in rows[start:]]


def _changed_since_ledger(rows: list[dict[str, Any]]) -> list[str]:
    """Claims touched after the last ledger approval, for the draft gate."""
    start = None
    for index, row in enumerate(rows):
        if (
            row.get("event") == "gate-decided"
            and row.get("gate") == Gate.LEDGER
            and row.get("outcome") == "approve"
        ):
            start = index + 1
    if start is None:
        return []
    touched = (
        row.get("id") or row.get("claim")
        for row in rows[start:]
        if str(row.get("event", "")).startswith("claim-")
    )
    return list(dict.fromkeys(claim for claim in touched if claim))


def check_view(run: Run) -> dict[str, Any]:
    """The gate summary and the evidence ledger, for the human."""
    state, meta = run.state, run.meta
    ledger = []
    missing = []
    for claim_id, claim in state.claims.items():
        exists = None
        if claim.artifact is not None:
            exists = meta.artifact(claim.artifact).exists()
            if claim.status in EVIDENCED and not exists:
                missing.append(
                    f"claim {claim_id}'s artifact {claim.artifact} does not exist"
                )
        ledger.append({"claim": claim_id, **claim.model_dump(), "exists": exists})
    document: dict[str, Any] = {"session": run.directory.name, "stage": state.stage}
    gate = _focus(state)
    if gate is not None:
        found = blockers(state, gate) + (missing if gate is Gate.DRAFT else [])
        document["gate"] = {
            "name": gate,
            "stage": GATE_STAGE[gate],
            "artifact": ARTIFACT[gate],
            "standing": state.gates[gate],
            "blockers": found,
        }
        if gate is Gate.DRAFT:
            document["gate"]["claims_changed_since_ledger"] = _changed_since_ledger(
                run.rows
            )
    document["since_last_decision"] = _since_last_decision(run.rows)
    document["ledger"] = ledger
    document["dropped"] = [
        {"claim": claim_id, "reason": reason}
        for claim_id, reason in state.dropped.items()
    ]
    document["missing_artifacts"] = missing
    document["next"] = next_step(state)
    return document
