"""What a run pins at intake: the session marker, the verb, and the stages
and gates the verb spans."""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from btm_corekit import Diagnostic, NonEmpty, SessionStore, Tagged, refuse

STORE = SessionStore("draft-paper", marker="run.json", hint="run init first")
TRACE = "trace.jsonl"


class Verb(StrEnum):
    DESIGN = "design"
    BUILD = "build"
    REFACTOR = "refactor"
    REBUT = "rebut"


class Format(StrEnum):
    SHORT = "short"
    FULL = "full"
    WORKSHOP = "workshop"
    JOURNAL = "journal"
    SURVEY = "survey"
    DEMO = "demo"


class InputState(StrEnum):
    SPARK = "spark"
    SHAPED = "shaped"
    PARTIAL = "partial"
    FULL = "full"
    DRAFT = "draft"
    REVIEWS = "reviews"


STARTS: dict[Verb, tuple[InputState, ...]] = {
    Verb.DESIGN: (InputState.SPARK, InputState.SHAPED),
    Verb.BUILD: (InputState.SHAPED, InputState.PARTIAL, InputState.FULL),
    Verb.REFACTOR: (InputState.DRAFT,),
    Verb.REBUT: (InputState.REVIEWS,),
}


class Gate(StrEnum):
    """The human approval points, each closing one stage."""

    PLAN = "plan"
    LEDGER = "ledger"
    DRAFT = "draft"


GATE_STAGE: dict[Gate, int] = {Gate.PLAN: 1, Gate.LEDGER: 2, Gate.DRAFT: 8}


class RunMeta(Tagged):
    """Fixed at init but for the corpus and links `attach` sets; the marker
    file that witnesses a session."""

    run: NonEmpty
    verb: Verb
    format: Format
    state: InputState
    venue: NonEmpty
    model: NonEmpty
    artifacts: NonEmpty  # the root at init; `artifacts-repinned` moves it
    created: str = ""
    corpus: str | None = None  # the attached lit-review `papers.jsonl`, set by attach

    @model_validator(mode="after")
    def _verb_fits_state(self) -> RunMeta:
        allowed = STARTS[self.verb]
        if self.state not in allowed:
            refuse(
                "RunMeta",
                [
                    Diagnostic(
                        "state",
                        f"a {self.verb} run starts from "
                        f"{' or '.join(allowed)}, not {self.state}",
                    )
                ],
            )
        return self

    def stages(self) -> tuple[int, int]:
        """First and last stage the verb runs; build validates a shaped
        idea's positioning before its evidence. Design ends at the plan gate,
        which approves the prospective ledger with the plan."""
        match self.verb:
            case Verb.DESIGN:
                return 1, 1
            case Verb.BUILD:
                return (1 if self.state is InputState.SHAPED else 2), 8
            case Verb.REFACTOR:
                return 3, 8
            case Verb.REBUT:
                return 9, 9

    def gates(self) -> tuple[Gate, ...]:
        first, last = self.stages()
        return tuple(gate for gate in Gate if first <= GATE_STAGE[gate] <= last)
