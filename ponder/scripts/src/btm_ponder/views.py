"""Derived views: the drafting scaffold read off a replayed ledger."""

from __future__ import annotations

from typing import Any

from btm_corekit import JSON, View
from btm_ponder.state import (
    CHAIN_MIN_LINKS,
    SETTLING,
    Folded,
    LeafState,
    Ledger,
    Open,
    Refuted,
    Retired,
    Retrieved,
    SourceClass,
    Sweep,
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
    states = [leaf.state for leaf in ledger.leaves.values()]
    if sum(isinstance(s, Retrieved) for s in states) > CHAIN_MIN_LINKS:
        derived.append("chain")
    if any(isinstance(s, Refuted) for s in states) or ledger.swept:
        derived.append("rival")
    if any(isinstance(s, Unresolved) for s in states):
        derived.append("open")
    derived.append("sources")
    return derived


OPEN_LEAF = "open leaf blocks draft"
NO_SWEEP = "no sweep recorded"
INFORMAL_DEMOTED = (OPEN_LEAF, NO_SWEEP)  # advisories, not blockers, when informal


def violations(ledger: Ledger) -> list[str]:
    found = [
        f"{OPEN_LEAF}: {leaf_id} ({leaf.question})"
        for leaf_id, leaf in ledger.leaves.items()
        if isinstance(leaf.state, Open)
    ]
    if not ledger.swept:
        found.append(f"{NO_SWEEP}: run the rival sweep before drafting")
    for leaf_id, leaf in ledger.leaves.items():
        if isinstance(leaf.state, Folded):
            target = ledger.leaves.get(leaf.state.into)
            if target is None or not isinstance(target.state, Retrieved):
                found.append(
                    f"fold broken: {leaf_id} folded into {leaf.state.into}, "
                    "which is no longer retrieved; reopen or re-close the fold"
                )
    return found


def hedges(ledger: Ledger) -> list[str]:
    """Advisory: leaves whose evidence class earns hedged wording."""
    lines = []
    for leaf_id, leaf in ledger.leaves.items():
        if isinstance(leaf.state, (Retrieved, Refuted)):
            classes = [ledger.sources[sid].cls for sid in leaf.state.sources]
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
            searches = raw.get("searches", 0)
            rows.append(
                {
                    "label": raw.get("label") or f"round-{len(rows) + 1}",
                    "searches": searches,
                    "new_sources": new_sources,
                    "yield": round(new_sources / searches, 2) if searches else None,
                }
            )
            new_sources = 0
    return rows


def leaf_view(state: LeafState) -> dict[str, Any]:
    match state:
        case Open():
            return {"state": "open"}
        case Retrieved(sources=sources, premise=premise, detail=detail):
            view = {"state": "retrieved", "sources": list(sources)}
            return view | _prose(premise, detail)
        case Refuted(sources=sources, premise=premise, detail=detail):
            view = {"state": "refuted", "sources": list(sources), "premise": premise}
            return view | _prose("", detail)
        case Unresolved(reason=reason, detail=detail):
            return {"state": "unresolved", "reason": reason, "detail": detail}
        case Retired(detail=detail):
            return {"state": "retired", "detail": detail}
        case Folded(into=into):
            return {"state": "folded", "into": into}


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


def _sweep_row(sweep: Sweep, view: View) -> dict[str, Any]:
    """What a sweep contributes to the Rival section: the survivors, and the
    set difference the section reports as eliminated. Hashing the survivors
    keeps it O(candidates) rather than a scan per candidate.

    `checked` names the sweep and stays at every level; the candidate text is
    the agent's own, so it arrives with the rest of the prose at `draft`."""
    row: dict[str, Any] = {"checked": sweep.checked}
    if not view.covers(View.DRAFT):
        return row
    survived = frozenset(sweep.survivors)
    row["survivors"] = list(sweep.survivors)
    row["eliminated"] = [name for name in sweep.candidates if name not in survived]
    return row


def marker_table(ledger: Ledger, marker_of: dict[str, str]) -> dict[str, JSON]:
    """Marker to the three fields a Sources line needs. The minted id is the
    ledger's business, not the draft's, and 41 of them cost 1.9 KB no reader
    spends."""
    return {
        marker_of[source_id]: {
            "cls": ledger.sources[source_id].cls,
            "title": ledger.sources[source_id].title,
            "url": ledger.sources[source_id].url,
        }
        for source_id in ledger.source_order
    }


def scaffold(
    ledger: Ledger, marker_of: dict[str, str], view: View = View.DRAFT
) -> dict[str, list[dict[str, Any]]]:
    """The stored close prose keyed by marker, grouped into the derived sections.

    One rule across all four row kinds: a row carries its identity and its
    derivation at every level, and the agent's own findings only from `draft`.
    Identity is the leaf id, its question, and a sweep's subject; derivation is
    the marker refs, the hedge class, and an unresolved leaf's reason, which is
    a closed vocabulary rather than prose. Withheld below `draft`: premise,
    detail, survivors, eliminated. Those are worth their bytes after a
    compaction and worth nothing in the window that wrote them."""
    prose = _prose if view.covers(View.DRAFT) else _no_prose
    body: dict[str, list[dict[str, Any]]] = {"answer": [], "rival": [], "open": []}
    for leaf_id, leaf in ledger.leaves.items():
        match leaf.state:
            case Retrieved(sources=sources, premise=premise, detail=detail):
                classes = [ledger.sources[sid].cls for sid in sources]
                body["answer"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "markers": [marker_of[sid] for sid in sources],
                        "stated": stated(classes),
                    }
                    | prose(premise, detail)
                )
            case Refuted(sources=sources, premise=premise, detail=detail):
                body["rival"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "markers": [marker_of[sid] for sid in sources],
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
    body["sweeps"] = [_sweep_row(sweep, view) for sweep in ledger.sweeps]
    return {section: rows for section, rows in body.items() if rows}


def counts_of(ledger: Ledger) -> dict[str, int]:
    tally: dict[str, int] = {}
    for leaf in ledger.leaves.values():
        key = leaf_view(leaf.state)["state"]
        tally[key] = tally.get(key, 0) + 1
    return tally
