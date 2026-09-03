"""The leaf-state sum, the records built on it, and the ledger value."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SourceClass(StrEnum):
    """What a source is relative to the question it answers. The first two
    can settle a leaf alone; MEASURED needs corroboration; REPORTED supports
    only hedged claims. `stated` is the eliminator that reads that order."""

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


CLOSE_STATES = ("retrieved", "refuted", "unresolved", "retired", "folded")
# The validation surfaces read their vocabulary off the type, so a variant
# cannot be added in one place and forgotten in the other.
SOURCE_CLASSES = tuple(SourceClass)
ORIGINS = tuple(Origin)
MODES = tuple(Mode)
UNRESOLVED_REASONS = tuple(Reason)
CHAIN_MIN_LINKS = 2  # a Chain section renders past this many retrieved leaves


@dataclass(frozen=True, slots=True)
class Open:
    pass


@dataclass(frozen=True, slots=True)
class Retrieved:
    sources: tuple[str, ...]  # non-empty by construction
    premise: str = ""  # the claim, one line; comes back in the check scaffold
    detail: str = ""  # supporting note, likewise


@dataclass(frozen=True, slots=True)
class Refuted:
    sources: tuple[str, ...]  # non-empty by construction
    premise: str  # what the leaf assumed that evidence contradicts
    detail: str = ""  # supporting note, likewise


@dataclass(frozen=True, slots=True)
class Unresolved:
    reason: Reason
    detail: str


@dataclass(frozen=True, slots=True)
class Retired:
    detail: str  # why the leaf fails to change the conclusion


@dataclass(frozen=True, slots=True)
class Folded:
    into: str  # the retrieved leaf that absorbed this one


LeafState = Open | Retrieved | Refuted | Unresolved | Retired | Folded


@dataclass(frozen=True, slots=True)
class Leaf:
    question: str
    origin: Origin
    state: LeafState


@dataclass(frozen=True, slots=True)
class Sweep:
    """One rival sweep. Held by its decoder: `checked` is non-empty and
    `survivors` is a subset of `candidates`, so a Rival section can be
    rendered from the ledger rather than from the agent's memory."""

    checked: str
    candidates: tuple[str, ...]
    survivors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Source:
    leaf: str
    cls: SourceClass
    title: str
    url: str


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
