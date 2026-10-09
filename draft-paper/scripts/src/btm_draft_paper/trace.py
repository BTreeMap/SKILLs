"""The run trace: the closed event vocabulary, the transition law, and
replay. Every command replays the whole log, so a stage, a gate standing, or
a claim's status is derived from it on each call and never stored."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, assert_never

from pydantic import ConfigDict, Field, TypeAdapter, model_validator

from btm_corekit import (
    MAX_EVENTS,
    CommandError,
    Diagnostic,
    EventLog,
    Model,
    NonEmpty,
    Positive,
    Slug,
    demand,
    dump,
    parse_model,
    parse_with,
    refuse,
    require,
)
from btm_draft_paper.run import (
    GATE_STAGE,
    STORE,
    TRACE,
    Gate,
    RunMeta,
    Verb,
)

Stage = Annotated[Positive, Field(le=9)]


class Outcome(StrEnum):
    """What the human may answer at a gate."""

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


class Status(StrEnum):
    """A claim's evidential standing in the ledger."""

    SUPPORTED = "supported"
    EXPLORATORY = "exploratory"
    UNSUPPORTED = "unsupported"
    TO_RUN = "to-run"


EVIDENCED = frozenset({Status.SUPPORTED, Status.EXPLORATORY})
"""Statuses whose artifact must exist and name a location."""
NEEDS_ARTIFACT = EVIDENCED | {Status.TO_RUN}
UNSHIPPABLE = frozenset({Status.UNSUPPORTED, Status.TO_RUN})


class Standing(StrEnum):
    """A gate's derived state."""

    OPEN = "open"
    PENDING = "pending"
    APPROVED = "approved"
    REVISE = "revise"
    REJECTED = "rejected"


DECIDED = {
    Outcome.APPROVE: Standing.APPROVED,
    Outcome.REVISE: Standing.REVISE,
    Outcome.REJECT: Standing.REJECTED,
}


class Claim(Model):
    """One ledger row. The artifact law lives here, so a revision that breaks
    it is refused like an addition that does."""

    text: NonEmpty
    status: Status
    artifact: NonEmpty | None = None
    location: NonEmpty | None = None

    @model_validator(mode="after")
    def _evidence_named(self) -> Claim:
        problems = []
        if self.status in NEEDS_ARTIFACT and self.artifact is None:
            problems.append(
                Diagnostic("artifact", f"a {self.status} claim names its artifact path")
            )
        if self.status in EVIDENCED and self.location is None:
            problems.append(
                Diagnostic(
                    "location", f"a {self.status} claim names where in the artifact"
                )
            )
        if problems:
            refuse("Claim", problems)
        return self


class StageEntered(Model):
    event: Literal["stage-entered"]
    stage: Stage


class GateRequested(Model):
    event: Literal["gate-requested"]
    gate: Gate


class GateDecided(Model):
    event: Literal["gate-decided"]
    gate: Gate
    outcome: Outcome
    reply: NonEmpty


class ClaimAdded(Claim):
    event: Literal["claim-added"]
    id: Slug


class ClaimRevised(Model):
    event: Literal["claim-revised"]
    claim: NonEmpty
    text: NonEmpty | None = None
    status: Status | None = None
    artifact: NonEmpty | None = None
    location: NonEmpty | None = None

    @model_validator(mode="after")
    def _changes_something(self) -> ClaimRevised:
        if not self.changes():
            refuse(
                "ClaimRevised",
                [Diagnostic("claim", "add a text, status, artifact, or location")],
            )
        return self

    def changes(self) -> dict[str, Any]:
        return {
            key: value for key, value in dump(self).items() if key in Claim.model_fields
        }


class ClaimDropped(Model):
    event: Literal["claim-dropped"]
    claim: NonEmpty
    reason: NonEmpty


class ArtifactsRepinned(Model):
    """The artifact tree moved; claim paths resolve against `root` from here."""

    event: Literal["artifacts-repinned"]
    root: NonEmpty


class CitationAdded(Model):
    """One citation the draft makes: `ref` is a corpus key, DOI, or arXiv id.
    What it resolves to is derived on every `check`, never stored."""

    event: Literal["citation-added"]
    ref: NonEmpty
    sentence: NonEmpty


class Decision(Model):
    event: Literal["decision"]
    what: NonEmpty
    why: NonEmpty
    from_: tuple[str, ...] = Field(default=(), alias="from")


Event = (
    StageEntered
    | GateRequested
    | GateDecided
    | ClaimAdded
    | ClaimRevised
    | ClaimDropped
    | ArtifactsRepinned
    | CitationAdded
    | Decision
)
EVENT: TypeAdapter[Event] = TypeAdapter(Annotated[Event, Field(discriminator="event")])


class Stamp(Model):
    """The envelope the script writes around every event."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    t: datetime
    run: NonEmpty


STAMP_KEYS = frozenset(Stamp.model_fields)


@dataclass(slots=True)
class RunState:
    """What the trace says so far; built only by `apply`."""

    meta: RunMeta
    gates: dict[Gate, Standing]
    root: str
    stage: int | None = None
    closed: Gate | None = None
    claims: dict[str, Claim] = field(default_factory=dict)
    dropped: dict[str, str] = field(default_factory=dict)
    citations: list[CitationAdded] = field(default_factory=list)
    events: int = 0

    @classmethod
    def of(cls, meta: RunMeta) -> RunState:
        return cls(meta, dict.fromkeys(meta.gates(), Standing.OPEN), meta.artifacts)

    def artifact(self, path: str) -> Path:
        """A claim's artifact, relative to the latest artifact root."""
        given = Path(path).expanduser()
        return given if given.is_absolute() else Path(self.root) / given

    def gate_at(self, stage: int) -> Gate | None:
        return next((g for g in self.gates if GATE_STAGE[g] == stage), None)


def blockers(state: RunState, gate: Gate) -> list[str]:
    """What the trace alone says stands between a gate and its request."""
    match gate:
        case Gate.PLAN if state.meta.verb is Verb.DESIGN and not state.claims:
            return [
                "note each falsifiable claim as to-run: the plan carries the ledger"
            ]
        case Gate.PLAN:
            return []
        case Gate.LEDGER:
            return [] if state.claims else ["add at least one claim to the ledger"]
        case Gate.DRAFT:
            return [
                f"claim {claim_id} is {claim.status}: run it and revise the "
                "claim, or drop it"
                for claim_id, claim in state.claims.items()
                if claim.status in UNSHIPPABLE
            ]


def _enter(state: RunState, stage: int) -> None:
    first, last = state.meta.stages()
    require(
        first <= stage <= last,
        f"stage {stage} is outside a {state.meta.verb} run (stages {first}-{last})",
    )
    for gate, standing in state.gates.items():
        require(
            GATE_STAGE[gate] >= stage or standing is Standing.APPROVED,
            f"stage {stage} lies past the {gate} gate, which is {standing}; "
            "the human approves it first",
        )
    if (here := state.gate_at(stage)) is not None:
        state.gates[here] = Standing.OPEN  # re-entering a stage reopens its gate
    state.stage = stage


def _request(state: RunState, gate: Gate) -> None:
    require(
        gate in state.gates,
        f"a {state.meta.verb} run has no {gate} gate; its gates: "
        f"{', '.join(state.gates) or 'none'}",
    )
    require(
        state.stage == GATE_STAGE[gate],
        f"request the {gate} gate from stage {GATE_STAGE[gate]}; "
        f"the run is at stage {state.stage}",
    )
    standing = state.gates[gate]
    require(
        standing not in (Standing.PENDING, Standing.APPROVED),
        f"the {gate} gate is already {standing}",
    )
    found = blockers(state, gate)
    require(not found, "; ".join(found))
    state.gates[gate] = Standing.PENDING


def _decide(state: RunState, event: GateDecided) -> None:
    require(
        state.gates.get(event.gate) is Standing.PENDING,
        f"the {event.gate} gate has no pending request; note gate-requested first",
    )
    state.gates[event.gate] = DECIDED[event.outcome]
    if event.outcome is Outcome.REJECT:
        state.closed = event.gate


def _live(state: RunState, claim_id: str) -> Claim:
    dropped = " (dropped)" if claim_id in state.dropped else ""
    return demand(state.claims.get(claim_id), f"no live claim {claim_id}{dropped}")


def apply(state: RunState, raw: Mapping[str, Any]) -> None:
    """Admit one unstamped event into the state, or raise the law it breaks.
    The gate runs this on every staged event, so the log holds only events
    that replay."""
    require(state.events < MAX_EVENTS, f"event cap reached ({MAX_EVENTS})")
    require(
        state.closed is None,
        f"the human rejected the {state.closed} gate, which closed the run",
    )
    event = parse_with(EVENT, raw, "event")
    match event:
        case StageEntered(stage=stage):
            _enter(state, stage)
        case GateRequested(gate=gate):
            _request(state, gate)
        case GateDecided():
            _decide(state, event)
        case ClaimAdded(id=claim_id):
            require(claim_id not in state.claims, f"duplicate claim id: {claim_id}")
            state.claims[claim_id] = Claim.model_validate(
                {key: getattr(event, key) for key in Claim.model_fields}
            )
        case ClaimRevised(claim=claim_id):
            old = _live(state, claim_id)
            state.claims[claim_id] = parse_model(
                Claim, {**dump(old), **event.changes()}, f"claim {claim_id}"
            )
        case ClaimDropped(claim=claim_id, reason=reason):
            _live(state, claim_id)
            del state.claims[claim_id]
            state.dropped[claim_id] = reason
        case ArtifactsRepinned(root=root):
            require(Path(root).is_absolute(), f"artifact root {root!r} is not absolute")
            state.root = root
        case CitationAdded():
            state.citations.append(event)
        case Decision():
            pass
        case _:
            assert_never(event)
    state.events += 1


@dataclass(frozen=True, slots=True)
class Run:
    """One session read whole: its directory, pin, trace rows, and state."""

    directory: Path
    meta: RunMeta
    rows: list[dict[str, Any]]
    state: RunState


def load(session: str) -> Run:
    """Read and replay a session. The script alone writes the trace, so a
    line that does not decode or replay is an authoritative defect."""
    directory = STORE.directory(session)
    meta = STORE.read_meta(directory, RunMeta)
    rows = EventLog(directory / TRACE).read()
    state = RunState.of(meta)
    for number, raw in enumerate(rows, start=1):
        where = f"trace event {number}"
        stamp = parse_model(Stamp, raw, where)
        require(
            stamp.run == meta.run,
            f"{where}: run is {stamp.run!r}, the session's is {meta.run!r}",
        )
        payload = {key: value for key, value in raw.items() if key not in STAMP_KEYS}
        try:
            apply(state, payload)
        except CommandError as err:
            raise CommandError(f"{where} does not replay: {err}") from err
    return Run(directory, meta, rows, state)
