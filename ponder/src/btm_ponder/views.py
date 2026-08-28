"""Derived views: the drafting scaffold read off a replayed ledger."""

from __future__ import annotations

from typing import Any

from btm_ponder.state import (
    CHAIN_MIN_LINKS,
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


def violations(ledger: Ledger) -> list[str]:
    found = [
        f"open leaf blocks draft: {leaf_id} ({leaf.question})"
        for leaf_id, leaf in ledger.leaves.items()
        if isinstance(leaf.state, Open)
    ]
    if not ledger.swept:
        found.append("no sweep recorded: run the rival sweep before drafting")
    for leaf_id, leaf in ledger.leaves.items():
        if isinstance(leaf.state, Retired) and leaf.state.reason == "folded":
            target = ledger.leaves.get(leaf.state.detail)
            if target is None or not isinstance(target.state, Retrieved):
                found.append(
                    f"fold broken: {leaf_id} folded into {leaf.state.detail}, "
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
        case Retrieved(sources):
            return {"state": "retrieved", "sources": list(sources)}
        case Refuted(sources, premise):
            return {"state": "refuted", "sources": list(sources), "premise": premise}
        case Unresolved(reason, detail):
            return {"state": "unresolved", "reason": reason, "detail": detail}
        case Retired(reason, detail):
            return {"state": "retired", "reason": reason, "detail": detail}


def counts_of(ledger: Ledger) -> dict[str, int]:
    tally: dict[str, int] = {}
    for leaf in ledger.leaves.values():
        key = leaf_view(leaf.state)["state"]
        tally[key] = tally.get(key, 0) + 1
    return tally
