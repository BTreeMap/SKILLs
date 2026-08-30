"""The leaf-state sum, the records built on it, and the ledger value."""

from __future__ import annotations

from dataclasses import dataclass, field

from btm_corekit import CommandError

SOURCE_CLASSES = ("constitutive", "attested", "measured", "reported")
ORIGINS = ("frame", "spawned")
CLOSE_STATES = ("retrieved", "refuted", "unresolved", "retired")
MODES = ("full", "informal")  # informal demotes draft blockers to advisories
UNRESOLVED_REASONS = ("searched", "not_pursued")
RETIRED_REASONS = ("folded", "immaterial")
CHAIN_MIN_LINKS = 2  # a Chain section renders past this many retrieved leaves
MAX_EVENTS = 1000  # runaway backstop; a real run stays under ~100 events


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
    reason: str  # one of UNRESOLVED_REASONS
    detail: str


@dataclass(frozen=True, slots=True)
class Retired:
    reason: str  # one of RETIRED_REASONS
    detail: str  # folded: the target leaf id; immaterial: why


LeafState = Open | Retrieved | Refuted | Unresolved | Retired


@dataclass(frozen=True, slots=True)
class Leaf:
    question: str
    origin: str
    state: LeafState


@dataclass(frozen=True, slots=True)
class Source:
    leaf: str
    cls: str
    title: str
    url: str


@dataclass(slots=True)
class Ledger:
    """Left fold of the event log; mutated only inside apply()."""

    leaves: dict[str, Leaf] = field(default_factory=dict)
    sources: dict[str, Source] = field(default_factory=dict)
    source_order: list[str] = field(default_factory=list)
    swept: bool = False
    events: int = 0


def require(condition: bool, invariant: str) -> None:
    if not condition:
        raise CommandError(invariant)
