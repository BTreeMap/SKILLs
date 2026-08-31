"""Derived views: the drafting scaffold read off a replayed ledger."""

from __future__ import annotations

from typing import Any

from btm_ponder.state import (
    CHAIN_MIN_LINKS,
    Folded,
    LeafState,
    Ledger,
    Open,
    Refuted,
    Retired,
    Retrieved,
    Unresolved,
)


def stated(classes: list[str]) -> str:
    """How the renderer may voice a claim: advisory, never a close gate."""
    if any(cls in ("constitutive", "attested") for cls in classes):
        return "plain"
    measured = sum(1 for cls in classes if cls == "measured")
    return "plain" if measured >= 2 else "hedged"  # noqa: PLR2004


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
    rows = []
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
        case Retrieved(sources, premise, detail):
            view = {"state": "retrieved", "sources": list(sources)}
            return view | _prose(premise, detail)
        case Refuted(sources, premise, detail):
            view = {"state": "refuted", "sources": list(sources), "premise": premise}
            return view | _prose("", detail)
        case Unresolved(reason, detail):
            return {"state": "unresolved", "reason": reason, "detail": detail}
        case Retired(detail):
            return {"state": "retired", "detail": detail}
        case Folded(into):
            return {"state": "folded", "into": into}


def _prose(premise: str, detail: str) -> dict[str, str]:
    fields = {}
    if premise:
        fields["premise"] = premise
    if detail:
        fields["detail"] = detail
    return fields


def scaffold(ledger: Ledger, marker_of: dict[str, str]) -> dict[str, list[dict]]:
    """The stored close prose keyed by marker, grouped into the derived sections."""
    body: dict[str, list[dict]] = {"answer": [], "rival": [], "open": []}
    for leaf_id, leaf in ledger.leaves.items():
        match leaf.state:
            case Retrieved(sources, premise, detail):
                classes = [ledger.sources[sid].cls for sid in sources]
                body["answer"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "markers": [marker_of[sid] for sid in sources],
                        "stated": stated(classes),
                    }
                    | _prose(premise, detail)
                )
            case Refuted(sources, premise, detail):
                body["rival"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "markers": [marker_of[sid] for sid in sources],
                        "premise": premise,
                    }
                    | _prose("", detail)
                )
            case Unresolved(reason, detail):
                body["open"].append(
                    {
                        "leaf": leaf_id,
                        "q": leaf.question,
                        "reason": reason,
                        "detail": detail,
                    }
                )
            case Open() | Retired() | Folded():
                pass
    return {section: rows for section, rows in body.items() if rows}


def counts_of(ledger: Ledger) -> dict[str, int]:
    tally: dict[str, int] = {}
    for leaf in ledger.leaves.values():
        key = leaf_view(leaf.state)["state"]
        tally[key] = tally.get(key, 0) + 1
    return tally
