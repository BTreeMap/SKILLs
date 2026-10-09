"""The report, derived from state. Cost O(claims + evidence): one pass to
check, one to place, one to write; a run holds tens of claims."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum, auto

from btm_corekit import Admission
from btm_fact_check.state import (
    Claim,
    ClaimType,
    Confidence,
    Probe,
    Quoted,
    SideFinding,
    State,
    Verdict,
)

INDEPENDENT = 2
"""Publishers a correction needs under Invariant 4's general rule."""
CORRECTABLE = frozenset(
    {Verdict.CONTRADICTED, Verdict.OUTDATED, Verdict.MISSING_CONTEXT}
)


@dataclass(frozen=True, slots=True)
class Ready:
    """A claim whose verdict and confidence are both recorded; only these
    reach the writer, so it never meets a half-verified claim."""

    claim: Claim
    verdict: Verdict
    confidence: Confidence


class Section(Enum):
    CORRECTION = auto()
    JUDGMENT = auto()
    ACCURATE = auto()
    UNVERIFIED = auto()


def quotes(claim: Claim) -> list[Quoted]:
    return [entry for entry in claim.evidence if isinstance(entry, Quoted)]


def probes(claim: Claim) -> list[Probe]:
    return [entry for entry in claim.evidence if isinstance(entry, Probe)]


def owner_plus_probe(claim: Claim) -> bool:
    """Invariant 4's exception: one owner page and a live probe, spec only.
    Publishers compare case-folded; equal names are one organization."""
    publishers = {entry.publisher.casefold() for entry in quotes(claim)}
    return claim.type is ClaimType.SPEC and len(publishers) == 1 and bool(probes(claim))


def sourced(claim: Claim) -> bool:
    """Enough sources to carry a correction under Invariant 4. Two distinct
    publisher names is necessary, not sufficient: independence beyond the
    name stays the agent's judgment."""
    publishers = {entry.publisher.casefold() for entry in quotes(claim)}
    return len(publishers) >= INDEPENDENT or owner_plus_probe(claim)


def readiness(state: State) -> list[Ready] | Admission:
    """Every claim narrowed to `Ready`, or every problem found, at once."""
    gate = Admission()
    seen: Counter[str] = Counter(claim.id for claim in state.claims)
    ready: list[Ready] = []
    for index, claim in enumerate(state.claims):
        where = f"claims[{index}]"
        if seen[claim.id] > 1:
            gate.fail(f"{where}.id", f"give {claim.id} to one claim only")
        if claim.verdict is None:
            gate.fail(f"{where}.verdict", "verify this claim; record its verdict")
        if claim.confidence is None:
            gate.fail(f"{where}.confidence", "record the confidence band")
        if claim.verdict not in (None, Verdict.UNVERIFIABLE) and not quotes(claim):
            gate.fail(
                f"{where}.evidence",
                "cite at least one verbatim quote with URL and access date",
            )
        if claim.verdict is Verdict.UNVERIFIABLE and not claim.notes:
            gate.fail(f"{where}.notes", "give the reason this claim is unverifiable")
        if claim.correction is not None:
            if claim.verdict is not None and claim.verdict not in CORRECTABLE:
                gate.fail(
                    f"{where}.correction",
                    f"set null: a {claim.verdict} verdict takes no correction",
                )
            if claim.confidence is Confidence.LOW:
                gate.fail(f"{where}.correction", "set null: low confidence forces it")
            if not sourced(claim):
                gate.fail(
                    f"{where}.correction",
                    "set null, or cite two independent sources; a spec claim "
                    "may instead cite one owner page plus a live probe",
                )
        if claim.verdict is not None and claim.confidence is not None:
            ready.append(Ready(claim, claim.verdict, claim.confidence))
    return gate if gate.problems else ready


def section(item: Ready) -> Section:
    match item.verdict:
        case Verdict.SUPPORTED:
            return Section.ACCURATE
        case Verdict.INSUFFICIENT_EVIDENCE | Verdict.UNVERIFIABLE:
            return Section.UNVERIFIED
        case Verdict.CONFLICTING:
            return Section.JUDGMENT
        case Verdict.CONTRADICTED | Verdict.OUTDATED | Verdict.MISSING_CONTEXT:
            if item.claim.correction is None:
                return Section.JUDGMENT
            return Section.CORRECTION


def quoted_block(text: str) -> str:
    return "\n".join(f"> {line}" for line in text.splitlines() or [""])


def cited(entry: Quoted | Probe) -> str:
    match entry:
        case Quoted():
            published = entry.published or "unknown"
            return (
                f'"{entry.quote}" ({entry.publisher}, published {published}, '
                f"accessed {entry.accessed}, {entry.url})"
            )
        case Probe():
            keys = ", ".join(entry.keys) or "none"
            return (
                f"live probe {entry.probe} returned {entry.status}, "
                f"keys {keys} (accessed {entry.accessed})"
            )


def detail(item: Ready) -> str:
    claim = item.claim
    lines = [
        f"#### {claim.id} ({claim.type}, confidence {item.confidence}) "
        f"{claim.span.file}:{claim.span.lines}",
        "Document says:",
        quoted_block(claim.span.quote),
        "Evidence:",
        *(f"- {cited(entry)}" for entry in claim.evidence),
    ]
    if claim.correction is not None and owner_plus_probe(claim):
        lines.append("Rests on the owner plus the live probe.")
    lines.append(f"Counter-evidence or caveats: {claim.notes or 'none'}")
    if claim.correction is None:
        lines.append(f"Verdict: {item.verdict}. No correction proposed.")
    else:
        lines.append(f"Verdict: {item.verdict}. Proposed replacement:")
        lines.append(quoted_block(claim.correction))
    return "\n".join(lines)


def accurate(item: Ready) -> str:
    top = quotes(item.claim)[0]
    return f"- {item.claim.id}: {item.claim.claim} ({top.publisher}, {top.url})"


def unverified(item: Ready) -> str:
    reason = item.claim.notes or str(item.verdict)
    return f"- {item.claim.id}: {item.claim.claim} ({reason})"


def side(finding: SideFinding) -> str:
    return f"- {finding.finding} " + "; ".join(map(cited, finding.evidence))


def body(blocks: list[str], separator: str) -> str:
    return separator.join(blocks) if blocks else "None."


def report(state: State, ready: list[Ready]) -> str:
    """The Step 3 template, filled. Claims keep state order in each section;
    side findings appear only when some exist."""
    placed: dict[Section, list[Ready]] = {kind: [] for kind in Section}
    for item in ready:
        placed[section(item)].append(item)
    counts = Counter(item.verdict for item in ready)
    tally = ", ".join(f"{verdict} {counts[verdict]}" for verdict in Verdict)
    parts = [
        "## Fact-Check Report",
        f"Checked {len(ready)} claims from {state.file} "
        f"(claim-time: {state.claim_time or 'unknown'}).\n"
        f"Branch: {state.branch}; approx cost: {state.cost or 'n/a'}.\n"
        f"Verdicts: {tally}.",
        "### Corrections proposed",
        body(list(map(detail, placed[Section.CORRECTION])), "\n\n"),
        "### Needs your judgment (conflicting / abstained)",
        body(list(map(detail, placed[Section.JUDGMENT])), "\n\n"),
        "### Verified accurate",
        body(list(map(accurate, placed[Section.ACCURATE])), "\n"),
        "### Unverifiable / insufficient evidence",
        body(list(map(unverified, placed[Section.UNVERIFIED])), "\n"),
    ]
    if state.side_findings:
        parts += ["### Side findings", "\n".join(map(side, state.side_findings))]
    return "\n\n".join(parts) + "\n"
