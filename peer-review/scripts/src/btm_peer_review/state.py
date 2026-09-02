"""Records the ledger holds, their one decoder from disk, and the ledger value.

A record exists only through its parser, so every field a view reads is
already inside the closed vocabulary and every cross-reference resolves.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from btm_corekit import parse_enum, require
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


def _strings(raw: Any, where: str) -> tuple[str, ...]:
    require(
        isinstance(raw, list) and all(isinstance(s, str) for s in raw),
        f"{where} must be a list of strings",
    )
    return tuple(raw)


def claim_from_event(raw: Mapping[str, Any]) -> Claim:
    verbatim, page = raw.get("verbatim"), raw.get("page")
    require(isinstance(verbatim, str) and bool(verbatim), "claim event lacks verbatim")
    require(isinstance(page, int) and page > 0, "claim event lacks a page")
    return Claim(verbatim, page)


def objection_from_event(
    raw: Mapping[str, Any], claims: Mapping[str, Claim]
) -> Objection:
    """The decoder: disk shape to domain value, or a loud CommandError."""
    kind = parse_enum(Kind, raw.get("kind"), "objection kind")
    severity = parse_enum(Severity, raw.get("severity"), "objection severity")
    text = raw.get("text")
    require(isinstance(text, str) and bool(text), "objection event lacks text")
    claim = raw.get("claim")
    require(
        claim is None or claim in claims, f"objection cites unknown claim {claim!r}"
    )
    where = raw.get("where")
    require(where is None or isinstance(where, str), "objection where must be text")
    anchors = _strings(raw.get("anchors", []), "objection anchors")
    missing = raw.get("missing")
    evidence: Evidence
    if anchors:
        require(missing is None, "objection carries both anchors and missing")
        evidence = Quoted(anchors)
    else:
        require(isinstance(missing, str) and bool(missing), "objection lacks evidence")
        evidence = Missing(missing)
    prior = _strings(raw.get("prior", []), "objection prior")
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
