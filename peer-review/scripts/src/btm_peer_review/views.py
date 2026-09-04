"""Derived views: every standing, ratio, and recommendation is a function of
the ledger, the live paper text, and the linked corpus. Nothing here is stored.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, NotRequired, TypedDict

from btm_corekit import JSON, bracketed, is_digits
from btm_peer_review.constants import (
    ECHO_WARN,
    LEVEL_BANKS,
    Band,
    Bank,
    ClaimVerdict,
    Kind,
    Level,
    Recommendation,
    Severity,
    Standing,
)
from btm_peer_review.state import Ledger, Missing, Objection
from btm_peer_review.store import Corpus
from btm_peer_review.text import Fuzzy, PaperText, Unresolved, Verbatim

DECISIVE = frozenset({Severity.FATAL, Severity.MAJOR})


class AnchorView(TypedDict):
    quote: str
    page: int | None
    mode: str


class ObjectionView(TypedDict):
    """One objection as every downstream view reads it. Five functions index
    this by key, so the keys are the contract between them."""

    marker: str
    id: str
    kind: Kind
    bank: Bank
    severity: Severity
    standing: Standing
    claim: str | None
    where: str | None
    text: str
    anchors: list[AnchorView]
    missing: str | None
    prior: list[dict[str, JSON]]
    in_limitations: bool
    withdrawn: str | None


class ClaimView(TypedDict):
    marker: str
    id: str
    verbatim: str
    page: int | None
    verdict: ClaimVerdict
    objections: list[str]


def markers(ledger: Ledger) -> tuple[dict[str, str], dict[str, str]]:
    claims = {cid: f"C{i}" for i, cid in enumerate(ledger.claim_order, start=1)}
    objections = {oid: f"O{i}" for i, oid in enumerate(ledger.objection_order, start=1)}
    return claims, objections


def _anchor_views(
    objection: Objection, paper: PaperText | None
) -> tuple[list[AnchorView], bool, bool]:
    """Anchor rows, whether all resolve, whether any sits in Limitations."""
    if isinstance(objection.evidence, Missing):
        return [], True, False
    rows: list[AnchorView] = []
    grounded = True
    echoed = False
    for quote in objection.evidence.anchors:
        if paper is None:
            rows.append({"quote": quote, "page": None, "mode": "unread"})
            grounded = False
            continue
        match paper.resolve(quote):
            case Verbatim(page, offset):
                rows.append({"quote": quote, "page": page, "mode": "exact"})
                echoed = echoed or paper.in_limitations(offset)
            case Fuzzy(page, offset, _):
                rows.append({"quote": quote, "page": page, "mode": "fuzzy"})
                echoed = echoed or paper.in_limitations(offset)
            case Unresolved():
                rows.append({"quote": quote, "page": None, "mode": "unresolved"})
                grounded = False
    return rows, grounded, echoed


def _prior_views(
    objection: Objection, corpus: Corpus | None, year: int
) -> tuple[list[dict[str, JSON]], bool]:
    """Prior rows and whether every key resolves to a record dated at or
    before the paper; an objection without prior keys is dated by construction."""
    rows: list[dict[str, Any]] = []
    dated = True
    for key in objection.prior:
        record = corpus.lookup(key) if corpus else None
        if record is None:
            rows.append({"key": key, "year": None, "title": None, "status": "absent"})
            dated = False
            continue
        rows.append(
            {
                "key": record.key,
                "year": record.year,
                "title": record.title,
                "status": record.status,
            }
        )
        dated = dated and record.year is not None and record.year <= year
    return rows, dated


def _standing(withdrawn: bool, anchored: bool, dated: bool) -> Standing:
    if withdrawn:
        return Standing.WITHDRAWN
    if not anchored:
        return Standing.UNANCHORED
    if not dated:
        return Standing.UNDATED
    return Standing.GROUNDED


def objection_views(
    ledger: Ledger, paper: PaperText | None, corpus: Corpus | None, year: int
) -> list[ObjectionView]:
    claim_markers, objection_markers = markers(ledger)
    views: list[ObjectionView] = []
    for oid in ledger.objection_order:
        objection = ledger.objections[oid]
        anchors, anchored, echoed = _anchor_views(objection, paper)
        prior, dated = _prior_views(objection, corpus, year)
        views.append(
            ObjectionView(
                marker=objection_markers[oid],
                id=oid,
                kind=objection.kind,
                bank=objection.kind.bank,
                severity=objection.severity,
                standing=_standing(oid in ledger.withdrawn, anchored, dated),
                claim=claim_markers[objection.claim] if objection.claim else None,
                where=objection.where,
                text=objection.text,
                anchors=anchors,
                missing=(
                    objection.evidence.what
                    if isinstance(objection.evidence, Missing)
                    else None
                ),
                prior=prior,
                in_limitations=echoed,
                withdrawn=ledger.withdrawn.get(oid),
            )
        )
    return views


def _claim_verdict(hits: list[ObjectionView]) -> ClaimVerdict:
    if any(v["severity"] in DECISIVE for v in hits):
        return ClaimVerdict.CONTESTED
    return ClaimVerdict.QUESTIONED if hits else ClaimVerdict.STANDING


def claim_views(
    ledger: Ledger, paper: PaperText | None, objections: list[ObjectionView]
) -> list[ClaimView]:
    claim_markers, _ = markers(ledger)
    against: dict[str, list[ObjectionView]] = {m: [] for m in claim_markers.values()}
    for view in objections:
        if view["claim"] and view["standing"] is Standing.GROUNDED:
            against[view["claim"]].append(view)
    views: list[ClaimView] = []
    for cid in ledger.claim_order:
        claim = ledger.claims[cid]
        marker = claim_markers[cid]
        hits = against[marker]
        page: int | None = claim.page
        if paper is not None:
            match paper.resolve(claim.verbatim):
                case Verbatim(found, _) | Fuzzy(found, _, _):
                    page = found
                case Unresolved():
                    page = None
        views.append(
            ClaimView(
                marker=marker,
                id=cid,
                verbatim=claim.verbatim,
                page=page,
                verdict=_claim_verdict(hits),
                objections=[v["marker"] for v in hits],
            )
        )
    return views


def echo_ratio(
    objections: list[ObjectionView], paper: PaperText | None
) -> dict[str, JSON]:
    """Share of grounded, quoted objections whose anchor sits in the paper's
    own Limitations section: the author-echo measure."""
    if paper is None or paper.limitations is None:
        return {"ratio": None, "note": "no Limitations heading found in the paper"}
    anchored = [
        v for v in objections if v["standing"] is Standing.GROUNDED and v["anchors"]
    ]
    if not anchored:
        return {"ratio": None, "note": "no anchored objection yet"}
    inside = sum(1 for v in anchored if v["in_limitations"])
    ratio = round(inside / len(anchored), 2)
    return {
        "ratio": ratio,
        "inside": inside,
        "anchored": len(anchored),
        "warn": ratio >= ECHO_WARN,
    }


def recommendation(objections: list[ObjectionView]) -> dict[str, JSON]:
    """Severity rule over grounded objections; no free score."""
    counts = Counter(
        v["severity"] for v in objections if v["standing"] is Standing.GROUNDED
    )
    if counts[Severity.FATAL]:
        verdict = Recommendation.REJECT
    elif counts[Severity.MAJOR]:
        verdict = Recommendation.MAJOR_REVISION
    elif counts[Severity.MINOR]:
        verdict = Recommendation.MINOR_REVISION
    else:
        verdict = Recommendation.NONE
    return {"verdict": verdict, "grounded": {s: counts[s] for s in Severity}}


class Coverage(TypedDict):
    """What the review has walked. Indexed by the check command, so its shape
    outlives the return."""

    level: Level
    walked: list[Bank]
    unwalked: list[Bank]
    corpus: str | None
    pages: int
    confidence: Band


def coverage(
    ledger: Ledger, level: Level, corpus: Corpus | None, paper: PaperText | None
) -> Coverage:
    required = LEVEL_BANKS[level]
    walked = [bank for bank in required if bank in ledger.walks]
    unwalked = [bank for bank in required if bank not in ledger.walks]
    if paper is None:
        band = Band.NONE
    elif not unwalked and (corpus is not None or Bank.NOVELTY not in required):
        band = Band.HIGH
    elif len(walked) * 2 >= len(required):
        band = Band.MEDIUM
    else:
        band = Band.LOW
    return {
        "level": level,
        "walked": walked,
        "unwalked": unwalked,
        "corpus": corpus.path.as_posix() if corpus else None,
        "pages": len(paper.pages) if paper else 0,
        "confidence": band,
    }


def scaffold(
    claims: list[ClaimView], objections: list[ObjectionView]
) -> dict[str, JSON]:
    """The report's sections, derived: grounded objections by severity, the
    rest listed where the draft must disclose or drop them."""
    grounded = [v for v in objections if v["standing"] is Standing.GROUNDED]
    by_severity = {
        s: [v["marker"] for v in grounded if v["severity"] is s] for s in Severity
    }
    by_standing = {
        s: [v["marker"] for v in objections if v["standing"] is s] for s in Standing
    }
    return {
        "claims": [c["marker"] for c in claims],
        "fatal": by_severity[Severity.FATAL],
        "major": by_severity[Severity.MAJOR],
        "minor": by_severity[Severity.MINOR],
        "questions": by_severity[Severity.QUESTION],
        "withdrawn": by_standing[Standing.WITHDRAWN],
        "unanchored": by_standing[Standing.UNANCHORED],
        "undated": by_standing[Standing.UNDATED],
    }


class Citations(TypedDict):
    """`recommendation` is spliced in by the command after the pure check."""

    markers: int
    problems: list[str]
    recommendation: NotRequired[dict[str, JSON]]


def cite_check(
    text: str, claims: list[ClaimView], objections: list[ObjectionView]
) -> Citations:
    """Pure verdict over a draft: every marker resolves to a grounded
    objection or a claim, and every grounded fatal or major objection is
    cited. O(draft + ledger)."""
    known_claims = {c["marker"] for c in claims}
    by_marker = {v["marker"]: v for v in objections}
    used = {
        content
        for content in bracketed(text)
        if content[:1] in ("C", "O") and is_digits(content[1:])
    }
    problems = []
    for marker in sorted(used):
        if marker in known_claims:
            continue
        view = by_marker.get(marker)
        if view is None:
            problems.append(f"[{marker}] was never minted; cite a marker from check")
        elif view["standing"] is not Standing.GROUNDED:
            problems.append(f"[{marker}] is {view['standing']}; drop it or restore it")
    for view in objections:
        if (
            view["standing"] is Standing.GROUNDED
            and view["severity"] in DECISIVE
            and view["marker"] not in used
        ):
            problems.append(
                f"[{view['marker']}] is a grounded {view['severity']} objection "
                "absent from the draft"
            )
    return {"markers": len(used), "problems": problems}
