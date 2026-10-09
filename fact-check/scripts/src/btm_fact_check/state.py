"""The state file's shapes. The agent writes the file, so every model
forbids an extra field: a typo is a located fix, not a dropped value."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from pydantic import Discriminator, Field, Tag

from btm_corekit import Model, NonEmpty


class ClaimType(StrEnum):
    SPEC = "spec"
    VERSION = "version"
    DATE = "date"
    STATISTIC = "statistic"
    COMPUTATION = "computation"
    QUOTATION = "quotation"
    OTHER = "other"


class Verdict(StrEnum):
    """In report order: the header counts follow this sequence."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    OUTDATED = "outdated"
    CONFLICTING = "conflicting"
    MISSING_CONTEXT = "missing-context"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    UNVERIFIABLE = "unverifiable"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Approval(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    USER_REJECTED = "user-rejected"
    APPLIED = "applied"


class Branch(StrEnum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class Quoted(Model):
    """A retrieved page, quoted verbatim."""

    quote: NonEmpty
    url: NonEmpty
    publisher: NonEmpty
    published: str | None = None
    accessed: NonEmpty


class Probe(Model):
    """One read-only call to a live endpoint: request, status, keys seen."""

    probe: NonEmpty
    status: Annotated[int, Field(ge=100, le=599)]
    keys: tuple[NonEmpty, ...] = ()
    accessed: NonEmpty


def evidence_kind(raw: Any) -> str:
    """Branch on structure: a `probe` field marks a live probe."""
    if isinstance(raw, dict):
        return "probe" if "probe" in raw else "quote"
    return "probe" if isinstance(raw, Probe) else "quote"


Evidence = Annotated[
    Annotated[Quoted, Tag("quote")] | Annotated[Probe, Tag("probe")],
    Discriminator(evidence_kind),
]


class Span(Model):
    file: NonEmpty
    lines: NonEmpty
    quote: NonEmpty


class Claim(Model):
    """An inventory entry; the verdict fields fill in as Step 2 completes."""

    id: NonEmpty
    claim: NonEmpty
    span: Span
    type: ClaimType
    verdict: Verdict | None = None
    confidence: Confidence | None = None
    evidence: tuple[Evidence, ...] = ()
    correction: str | None = None
    notes: str | None = None
    status: Approval = Approval.PENDING


class SideFinding(Model):
    finding: NonEmpty
    evidence: Annotated[tuple[Evidence, ...], Field(min_length=1)]


class State(Model):
    constraints: tuple[NonEmpty, ...]
    file: NonEmpty
    claim_time: str | None = None
    branch: Branch
    cost: str | None = None
    claims: tuple[Claim, ...]
    side_findings: tuple[SideFinding, ...] = ()
