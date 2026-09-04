"""The leaf-state sum, the records built on it, and the ledger value."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from btm_corekit import Count, Model, NonEmpty, Slug


class SourceClass(StrEnum):
    """What a source is relative to the question it answers: the first two
    can settle a leaf alone, MEASURED needs corroboration, REPORTED supports
    only hedged claims."""

    CONSTITUTIVE = "constitutive"
    ATTESTED = "attested"
    MEASURED = "measured"
    REPORTED = "reported"


SETTLING = frozenset({SourceClass.CONSTITUTIVE, SourceClass.ATTESTED})


class Origin(StrEnum):
    """Whether a leaf came from the opening frame or was spawned mid-run."""

    FRAME = "frame"
    SPAWNED = "spawned"


class Reason(StrEnum):
    """Why a leaf stayed unresolved: looked and found nothing, or never
    pursued. The distinction is what a gap probe cites."""

    SEARCHED = "searched"
    NOT_PURSUED = "not_pursued"


class Mode(StrEnum):
    """INFORMAL demotes draft blockers to advisories; sourcing is unchanged."""

    FULL = "full"
    INFORMAL = "informal"


class CloseState(StrEnum):
    """How a leaf ends. The close decoder also accepts a legacy `retired`
    shape with reason `folded` as this state."""

    RETRIEVED = "retrieved"
    REFUTED = "refuted"
    UNRESOLVED = "unresolved"
    RETIRED = "retired"
    FOLDED = "folded"


CLOSE_STATES = tuple(CloseState)
# The validation surfaces read their vocabulary off the type, so a variant
# cannot be added in one place and forgotten in the other.
SOURCE_CLASSES = tuple(SourceClass)
ORIGINS = tuple(Origin)
MODES = tuple(Mode)
UNRESOLVED_REASONS = tuple(Reason)
CHAIN_MIN_LINKS = 2  # a Chain section renders past this many retrieved leaves


# Each variant names itself, so a count or a view reads the tag rather than
# rebuilding a dict to look at one key.
class Open(Model):
    state: Literal["open"] = "open"


class Retrieved(Model):
    state: Literal[CloseState.RETRIEVED] = CloseState.RETRIEVED
    sources: tuple[Slug, ...] = Field(min_length=1)
    premise: str = ""  # the claim, one line; comes back in the check scaffold
    detail: str = ""


class Refuted(Model):
    state: Literal[CloseState.REFUTED] = CloseState.REFUTED
    sources: tuple[Slug, ...] = Field(min_length=1)
    premise: NonEmpty  # what the leaf assumed that evidence contradicts
    detail: str = ""


class Unresolved(Model):
    state: Literal[CloseState.UNRESOLVED] = CloseState.UNRESOLVED
    reason: Reason
    detail: NonEmpty


class Retired(Model):
    state: Literal[CloseState.RETIRED] = CloseState.RETIRED
    detail: NonEmpty  # why the leaf fails to change the conclusion


class Folded(Model):
    state: Literal[CloseState.FOLDED] = CloseState.FOLDED
    into: Slug  # the retrieved leaf that absorbed this one


LeafState = Open | Retrieved | Refuted | Unresolved | Retired | Folded


class Leaf(Model):
    question: NonEmpty
    origin: Origin
    state: LeafState


class Sweep(Model):
    """Held by its decoder: `survivors` is a subset of `candidates`, so a
    Rival section renders from the ledger, not from the agent's memory."""

    checked: NonEmpty
    candidates: tuple[str, ...]
    survivors: tuple[str, ...]

    @model_validator(mode="after")
    def _survivors_came_from_the_candidates(self) -> Sweep:
        if not set(self.survivors) <= set(self.candidates):
            raise ValueError("sweep survivors must be a subset of candidates")
        return self


class Source(Model):
    leaf: Slug
    cls: SourceClass
    title: NonEmpty
    url: str


class Checkpoint(Model):
    """One round's declared search count; `label` names it in the yield table."""

    label: str = ""
    searches: Count


@dataclass(slots=True)
class Ledger:
    """Left fold of the event log; mutated only inside apply()."""

    leaves: dict[str, Leaf] = field(default_factory=dict)
    sources: dict[str, Source] = field(default_factory=dict)
    source_order: list[str] = field(default_factory=list)
    sweeps: list[Sweep] = field(default_factory=list)
    events: int = 0

    @property
    def swept(self) -> bool:
        """Derived, never stored: a sweep happened exactly when one is held."""
        return bool(self.sweeps)
