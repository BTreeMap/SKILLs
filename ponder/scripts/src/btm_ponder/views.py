"""Derived views: the drafting structure read off a replayed ledger."""

from __future__ import annotations

from collections import Counter
from typing import Any

from btm_corekit import JSON, View
from btm_ponder.state import (
    CHAIN_MIN_LINKS,
    SETTLING,
    Folded,
    LeafStatus,
    Ledger,
    Open,
    Refuted,
    Retired,
    Retrieved,
    Scan,
    SourceClass,
    Unresolved,
)

CORROBORATION = 2  # two measured sources carry a claim one cannot


def stated(classes: list[SourceClass]) -> str:
    """How the renderer may voice a claim: advisory, never a close gate.
    A settling class speaks plainly alone; measured evidence needs a second."""
    if any(cls in SETTLING for cls in classes):
        return "plain"
    measured = sum(1 for cls in classes if cls is SourceClass.MEASURED)
    return "plain" if measured >= CORROBORATION else "hedged"


def sections(ledger: Ledger) -> list[str]:
    """The five derivable sections; Boundary stays an agent judgment."""
    derived = ["answer"]
    statuses = [leaf.status for leaf in ledger.leaves.values()]
    if sum(isinstance(s, Retrieved) for s in statuses) > CHAIN_MIN_LINKS:
        derived.append("chain")
    if any(isinstance(s, Refuted) for s in statuses) or ledger.scanned:
        derived.append("rival")
    if any(isinstance(s, Unresolved) for s in statuses):
        derived.append("open")
    derived.append("sources")
    return derived


OPEN_LEAF = "open leaf blocks draft"
NO_SCAN = "no scan recorded"
BASIC_DEMOTED = (OPEN_LEAF, NO_SCAN)  # advisories, not blockers, at basic


def violations(ledger: Ledger) -> list[str]:
    found = [
        f"{OPEN_LEAF}: {leaf_id} ({leaf.question})"
        for leaf_id, leaf in ledger.leaves.items()
        if isinstance(leaf.status, Open)
    ]
    if not ledger.scanned:
        found.append(f"{NO_SCAN}: run the rival scan before drafting")
    for leaf_id, leaf in ledger.leaves.items():
        if isinstance(leaf.status, Folded):
            target = ledger.leaves.get(leaf.status.into)
            if target is None or not isinstance(target.status, Retrieved):
                found.append(
                    f"fold broken: {leaf_id} folded into {leaf.status.into}, "
                    "which is no longer retrieved; reopen or re-close the fold"
                )
    return found


def hedges(ledger: Ledger) -> list[str]:
    """Advisory: leaves whose evidence class earns hedged wording."""
    lines = []
    for leaf_id, leaf in ledger.leaves.items():
        if isinstance(leaf.status, (Retrieved, Refuted)):
            classes = [ledger.sources[sid].cls for sid in leaf.status.sources]
            if stated(classes) == "hedged":
                lines.append(
                    f"{leaf_id} rests on {'/'.join(sorted(set(classes)))} "
                    "sources: hedge the wording and name the class"
                )
    return lines


def yield_table(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """New sources per declared search, segmented by checkpoint events."""
    rows: list[dict[str, Any]] = []
    new_sources = 0
    for raw in events:
        if raw.get("e") == "add_source":
            new_sources += 1
        elif raw.get("e") == "checkpoint":
            queries = raw.get("queries", 0)
            rows.append(
                {
                    "label": raw.get("label") or f"cycle-{len(rows) + 1}",
                    "queries": queries,
                    "new_sources": new_sources,
                    "yield": round(new_sources / queries, 2) if queries else None,
                }
            )
            new_sources = 0
    return rows


def leaf_view(status: LeafStatus) -> dict[str, Any]:
    match status:
        case Open():
            return {"status": "open"}
        case Retrieved(sources=sources, premise=premise, detail=detail):
            view = {"status": "retrieved", "sources": list(sources)}
            return view | _prose(premise, detail)
        case Refuted(sources=sources, premise=premise, detail=detail):
            view = {"status": "refuted", "sources": list(sources), "premise": premise}
            return view | _prose("", detail)
        case Unresolved(reason=reason, detail=detail):
            return {"status": "unresolved", "reason": reason, "detail": detail}
        case Retired(detail=detail):
            return {"status": "retired", "detail": detail}
        case Folded(into=into):
            return {"status": "folded", "into": into}


def _no_prose(premise: str, detail: str) -> dict[str, str]:
    """The `plan` view's projection: the same shape, none of the payload."""
    return {}


def _prose(premise: str, detail: str) -> dict[str, str]:
    fields = {}
    if premise:
        fields["premise"] = premise
    if detail:
        fields["detail"] = detail
    return fields


def _scan_row(scan: Scan, view: View) -> dict[str, Any]:
    """What a scan contributes to the Rival section: the survivors, and the
    set difference the section reports as eliminated. Hashing the survivors
    keeps it O(candidates) rather than a pass per candidate."""
    row: dict[str, Any] = {"checked": scan.checked}
    if not view.covers(View.DRAFT):
        return row
    survived = frozenset(scan.survivors)
    row["survivors"] = list(scan.survivors)
    row["eliminated"] = [name for name in scan.candidates if name not in survived]
    return row


CITED_FIELDS = ("doi", "arxiv_id", "authors", "year", "venue")
"""What a source recorded from a `cite` record adds to its Sources line."""


def mark_table(ledger: Ledger, mark_of: dict[str, str]) -> dict[str, JSON]:
    """Mark to the fields a Sources line needs: class, title, url, and each
    citation field the source carries, an absent one costing nothing. The
    new id is the ledger's business, not the draft's, and 41 of them cost
    1.9 KB no reader spends."""
    table: dict[str, JSON] = {}
    for source_id in ledger.source_order:
        fields = ledger.sources[source_id].model_dump(mode="json")
        line = {name: fields[name] for name in ("cls", "title", "url")}
        line.update({name: fields[name] for name in CITED_FIELDS if fields[name]})
        table[mark_of[source_id]] = line
    return table


def structure(
    ledger: Ledger, mark_of: dict[str, str], view: View = View.DRAFT
) -> dict[str, list[dict[str, Any]]]:
    """The stored close prose keyed by mark, grouped into the derived sections.

    Every row carries its identity and derivation at every view level; the
    agent's own findings (premise, detail, survivors, eliminated) show only
    from `draft`, since they cost bytes no reader below that level spends."""
    prose = _prose if view.covers(View.DRAFT) else _no_prose
    body: dict[str, list[dict[str, Any]]] = {"answer": [], "rival": [], "open": []}
    for leaf_id, leaf in ledger.leaves.items():
        match leaf.status:
            case Retrieved(sources=sources, premise=premise, detail=detail):
                classes = [ledger.sources[sid].cls for sid in sources]
                body["answer"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "marks": [mark_of[sid] for sid in sources],
                        "stated": stated(classes),
                    }
                    | prose(premise, detail)
                )
            case Refuted(sources=sources, premise=premise, detail=detail):
                body["rival"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "marks": [mark_of[sid] for sid in sources],
                    }
                    | prose(premise, detail)
                )
            case Unresolved(reason=reason, detail=detail):
                body["open"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "reason": reason,
                    }
                    | prose("", detail)
                )
            case Open() | Retired() | Folded():
                pass
    body["scans"] = [_scan_row(scan, view) for scan in ledger.scans]
    return {section: rows for section, rows in body.items() if rows}


def counts_of(ledger: Ledger) -> dict[str, int]:
    """Each variant names itself, so this reads the tag."""
    return dict(Counter(leaf.status.status for leaf in ledger.leaves.values()))
