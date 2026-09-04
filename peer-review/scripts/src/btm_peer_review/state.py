"""Records the ledger holds and the ledger value.

A record exists only through its parser, so every field a view reads is
already inside the closed vocabulary and every cross-reference resolves.
The wire shapes that build them live in `ledger`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from btm_corekit import Model, NonEmpty, Positive, Trimmed, demand
from btm_peer_review.constants import ANCHOR_CHARS_MAX, Bank, Kind, Severity

Anchor = Annotated[
    str, Trimmed, StringConstraints(min_length=1, max_length=ANCHOR_CHARS_MAX)
]
"""A quote long enough to locate and short enough to align: one sentence."""


class Claim(Model):
    verbatim: NonEmpty
    page: Positive  # page at admission; check re-resolves against live text


class Quoted(Model):
    anchors: tuple[NonEmpty, ...] = Field(min_length=1)


class Missing(Model):
    what: NonEmpty  # what the paper omits, when nothing can be quoted


Evidence = Quoted | Missing


class Evidenced(Model):
    """Carries one kind of evidence. Both wire shapes that build an objection
    inherit it, so the law is stated once."""

    anchors: tuple[Anchor, ...] = ()
    missing: NonEmpty | None = None

    @model_validator(mode="after")
    def _one_kind_of_evidence(self) -> Evidenced:
        if bool(self.anchors) == bool(self.missing):
            raise ValueError(
                "quote the paper or name what it omits, never both and never neither"
            )
        return self

    @property
    def evidence(self) -> Evidence:
        """Total: the validator has already refused the other two shapes."""
        if self.anchors:
            return Quoted(anchors=self.anchors)
        return Missing(what=demand(self.missing, "objection lacks evidence"))


class Objection(Model):
    kind: Kind
    severity: Severity
    text: NonEmpty
    claim: str | None  # a claim id the objection contests
    where: str | None  # section or table, when a claim alone cannot place it
    evidence: Evidence
    prior: tuple[str, ...]  # corpus keys; non-empty exactly for the novelty bank

    @property
    def anchors(self) -> tuple[str, ...]:
        return self.evidence.anchors if isinstance(self.evidence, Quoted) else ()

    @model_validator(mode="after")
    def _prior_belongs_to_the_novelty_bank(self) -> Objection:
        if bool(self.prior) != (self.kind.bank is Bank.NOVELTY):
            raise ValueError(
                f"prior keys belong to novelty kinds alone; got {self.kind} "
                f"with {len(self.prior)}"
            )
        return self


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
