"""Records the ledger holds, their one decoder from disk, and the ledger value.

A record exists only through its parser, so every field a view reads is
already inside the closed vocabulary and every cross-reference resolves.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from btm_corekit import (
    parse_enum,
    read_count,
    read_opt_text,
    read_text,
    read_texts,
    require,
)
from btm_peer_review.constants import Bank, Kind, Severity


@dataclass(frozen=True, slots=True)
class Claim:
    verbatim: str
    page: int  # page at admission; check re-resolves against live text


@dataclass(frozen=True, slots=True)
class Quoted:
    anchors: tuple[str, ...]  # non-empty by construction


@dataclass(frozen=True, slots=True)
class Missing:
    what: str  # what the paper omits, when nothing can be quoted


Evidence = Quoted | Missing


@dataclass(frozen=True, slots=True)
class Objection:
    kind: Kind
    severity: Severity
    text: str
    claim: str | None  # a claim id the objection contests
    where: str | None  # section or table, when a claim alone cannot place it
    evidence: Evidence
    prior: tuple[str, ...]  # corpus keys; non-empty exactly for the novelty bank

    @property
    def anchors(self) -> tuple[str, ...]:
        return self.evidence.anchors if isinstance(self.evidence, Quoted) else ()


def claim_from_event(raw: Mapping[str, Any]) -> Claim:
    return Claim(
        read_text(raw, "verbatim", "claim event"),
        read_count(raw, "page", "claim event", minimum=1),
    )


def objection_from_event(
    raw: Mapping[str, Any], claims: Mapping[str, Claim]
) -> Objection:
    """The decoder: disk shape to domain value, or a loud CommandError."""
    kind = parse_enum(Kind, raw.get("kind"), "objection kind")
    severity = parse_enum(Severity, raw.get("severity"), "objection severity")
    text = read_text(raw, "text", "objection event")
    claim = raw.get("claim")
    require(
        claim is None or claim in claims, f"objection cites unknown claim {claim!r}"
    )
    where = read_opt_text(raw, "where", "objection")
    anchors = read_texts(raw, "anchors", "objection")
    # Not a kernel reader: the requirement is disjunctive, so "needs a
    # non-empty missing" would misstate it. Anchors satisfy it too.
    missing = read_opt_text(raw, "missing", "objection")
    evidence: Evidence
    if anchors:
        require(missing is None, "objection carries both anchors and missing")
        evidence = Quoted(anchors)
    else:
        require(bool(missing), "objection lacks evidence")
        evidence = Missing(missing or "")
    prior = read_texts(raw, "prior", "objection")
    require(
        bool(prior) == (kind.bank is Bank.NOVELTY),
        f"prior keys belong to novelty kinds alone; got {kind} with {len(prior)}",
    )
    return Objection(kind, severity, text, claim, where, evidence, prior)


@dataclass(slots=True)
class Ledger:
    """Left fold of the event log; mutated only inside apply()."""

    claims: dict[str, Claim] = field(default_factory=dict)
    claim_order: list[str] = field(default_factory=list)
    objections: dict[str, Objection] = field(default_factory=dict)
    objection_order: list[str] = field(default_factory=list)
    walks: dict[Bank, str] = field(default_factory=dict)  # bank -> note
    withdrawn: dict[str, str] = field(default_factory=dict)  # objection -> reason
    events: int = 0
