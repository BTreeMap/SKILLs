"""The note gate: decode, resolve, and simulate one batch of events; a
rejection lists every fix at once and the trace stays unchanged."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import ConfigDict

from btm_corekit import (
    Admission,
    CommandError,
    Diagnostic,
    Model,
    Named,
    Pool,
    dump,
    mint,
    suggest,
)
from btm_draft_paper.run import Gate
from btm_draft_paper.trace import (
    EVIDENCED,
    ArtifactsRepinned,
    Claim,
    ClaimDropped,
    ClaimRevised,
    Decision,
    GateDecided,
    GateRequested,
    Outcome,
    RunState,
    StageEntered,
    Status,
    apply,
)

SCHEMA: dict[str, str] = {
    "stage-entered": '{"event": "stage-entered", "stage": 1-9}',
    "gate-requested": '{"event": "gate-requested", "gate": "' + "|".join(Gate) + '"}',
    "gate-decided": '{"event": "gate-decided", "gate": "'
    + "|".join(Gate)
    + '", "outcome": "'
    + "|".join(Outcome)
    + '", "reply": "the human\'s reply, verbatim"}',
    "claim-added": '{"event": "claim-added", "kw": ["two", "words"], '
    '"text": "the claim as the draft states it", "status": "'
    + "|".join(Status)
    + '", "artifact": "path, relative to the artifact root", '
    '"location": "where in the artifact (supported and exploratory)"}',
    "claim-revised": '{"event": "claim-revised", "claim": "<ref>", '
    'plus any of "text", "status", "artifact", "location"}',
    "claim-dropped": '{"event": "claim-dropped", "claim": "<ref>", "reason": "..."}',
    "artifacts-repinned": '{"event": "artifacts-repinned", '
    '"root": "the artifact tree\'s new directory"}',
    "decision": '{"event": "decision", "what": "...", "why": "...", '
    '"from": ["<pad id>"] (optional)}',
}


class ClaimEntry(Claim, Named):
    """A claim as the agent writes it: keywords in place of the minted id."""

    event: Literal["claim-added"]


ROWS: dict[str, type[Model]] = {
    "stage-entered": StageEntered,
    "gate-requested": GateRequested,
    "gate-decided": GateDecided,
    "claim-added": ClaimEntry,
    "claim-revised": ClaimRevised,
    "claim-dropped": ClaimDropped,
    "artifacts-repinned": ArtifactsRepinned,
    "decision": Decision,
}


class NoteBatch(Model):
    """The container; rows decode one at a time so a bad row still lets its
    neighbours resolve."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    events: tuple[Mapping[str, Any], ...] = ()


@dataclass(slots=True)
class NoteResult:
    """Everything one batch produced; events commit only when problems is empty."""

    events: list[dict[str, Any]] = field(default_factory=list)
    minted: dict[str, str] = field(default_factory=dict)
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)


class _Expansion(Admission):
    """One batch: every method appends a problem and none raises."""

    def __init__(self, state: RunState, pad: Iterable[str]) -> None:
        super().__init__(mint, pad)
        self.state = state
        self.claims = Pool("claim", list(state.claims))
        self.staged: list[tuple[str, dict[str, Any]]] = []
        self.events: list[dict[str, Any]] = []

    def take(self, rows: Iterable[Mapping[str, Any]]) -> None:
        for index, row in enumerate(rows):
            where = f"events[{index}]"
            kind = row.get("event")
            model = ROWS.get(kind) if isinstance(kind, str) else None
            if model is None:
                near = suggest(str(kind), ROWS)
                self.fail(
                    f"{where}.event",
                    f"replace {kind!r}: it is no event kind",
                    f"did you mean: {', '.join(near)}"
                    if near
                    else f"valid kinds: {', '.join(ROWS)}",
                )
                continue
            entry = self.decode(model, row, where, SCHEMA[str(kind)])
            if entry is not None and (event := self.resolved(entry, where)):
                self.staged.append((where, event))

    def resolved(self, entry: Model, where: str) -> dict[str, Any] | None:
        """The event as it will be stored: ids minted, refs made full."""
        match entry:
            case ClaimEntry():
                claim_id = self.mint_id(entry, self.claims, where)
                if claim_id is None:
                    return None
                fields = dump(entry)
                return {
                    "event": "claim-added",
                    "id": claim_id,
                    **{key: fields[key] for key in Claim.model_fields if key in fields},
                }
            case ClaimRevised() | ClaimDropped():
                full = self.resolve_ref(entry.claim, self.claims, f"{where}.claim")
                return None if full is None else {**dump(entry), "claim": full}
            case ArtifactsRepinned():
                root = self.directory(entry.root, f"{where}.root")
                return None if root is None else {**dump(entry), "root": root}
            case Decision():
                linked = self.pad_links(entry.from_, where)
                return entry.model_dump(mode="json", by_alias=True) if linked else None
            case _:
                return dump(entry)

    def directory(self, given: str, where: str) -> str | None:
        """`given` made absolute against the current directory, when it names
        a directory; the trace stores roots absolute so replay needs no cwd."""
        root = Path(given).expanduser().resolve()
        if root.is_dir():
            return str(root)
        self.fail(where, f"{root} is not a directory")
        return None

    def simulate(self) -> None:
        """Apply staged events in order; a refusal becomes a located order,
        and a claim's artifact is checked on disk once it is evidenced."""
        for where, event in self.staged:
            kind = event["event"]
            before = self.state.stage
            try:
                apply(self.state, event)
            except CommandError as err:
                self.fail(where, str(err), SCHEMA[kind])
                continue
            self.events.append(event)
            if kind == "stage-entered":
                self.skipped(before, event["stage"], where)
            if kind in ("claim-added", "claim-revised"):
                self.artifact_exists(event.get("id") or event["claim"], where)
            if kind == "artifacts-repinned":
                self.lost_under_root(where)
            if kind == "gate-requested" and event["gate"] == Gate.DRAFT:
                for claim_id in self.state.claims:
                    self.artifact_exists(claim_id, where)

    def artifact_exists(self, claim_id: str, where: str) -> None:
        claim = self.state.claims[claim_id]
        if claim.status not in EVIDENCED or claim.artifact is None:
            return
        path = self.state.artifact(claim.artifact)
        if not path.exists():
            self.fail(
                where,
                f"claim {claim_id}'s artifact {path} does not exist: fix the "
                "path, mark the claim to-run or unsupported, or drop it",
            )

    def lost_under_root(self, where: str) -> None:
        """Advise on evidenced claims the new root does not hold; `check`
        and the draft gate act on them."""
        lost = [
            claim_id
            for claim_id, claim in self.state.claims.items()
            if claim.status in EVIDENCED
            and claim.artifact is not None
            and not self.state.artifact(claim.artifact).exists()
        ]
        if lost:
            self.advisories.append(
                f"{where}: the new root {self.state.root} lacks the artifact "
                f"of evidenced claims {', '.join(lost)}"
            )

    def skipped(self, before: int | None, stage: int, where: str) -> None:
        first = self.state.meta.stages()[0] if before is None else before + 1
        if stage == first + 1:
            self.advisories.append(f"{where} enters stage {stage}, skipping {first}")
        elif stage > first:
            self.advisories.append(
                f"{where} enters stage {stage}, skipping {first}-{stage - 1}"
            )


def expand_batch(
    state: RunState, batch: Mapping[str, Any], pad: Iterable[str] = ()
) -> NoteResult:
    """Expand one note batch into events, collecting every problem. The
    state passed in is advanced; on a non-empty problem list the caller
    discards it with the events."""
    expansion = _Expansion(state, pad)
    expansion.known_keys(batch, NoteBatch)
    note = expansion.families(batch, NoteBatch)
    expansion.take(note.events)
    if not expansion.staged and expansion.clean:
        expansion.fail("events", "add at least one event: the batch records nothing")
    expansion.simulate()
    return NoteResult(
        events=expansion.events,
        minted=expansion.claims.minted,
        advisories=expansion.advisories,
        problems=expansion.problems,
    )
