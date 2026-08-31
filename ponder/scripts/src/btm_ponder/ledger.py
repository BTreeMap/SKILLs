"""Event transitions: the smart constructor that decides what the log may hold."""

from __future__ import annotations

from typing import Any

from btm_corekit import CommandError
from btm_ponder.state import (
    CLOSE_STATES,
    MAX_EVENTS,
    ORIGINS,
    SOURCE_CLASSES,
    UNRESOLVED_REASONS,
    Folded,
    Leaf,
    LeafState,
    Ledger,
    Open,
    Refuted,
    Retired,
    Retrieved,
    Source,
    Unresolved,
    require,
)


def _close_state(raw: dict[str, Any], ledger: Ledger) -> LeafState:
    """Parse a close payload into a LeafState, or raise the violated invariant."""
    state = raw.get("state")
    if state == "retired" and raw.get("reason") == "folded":
        # Logs written before folded became its own state carry it this way.
        state = "folded"
        raw = {**raw, "into": raw.get("into") or raw.get("detail")}
    require(state in CLOSE_STATES, f"close state must be one of {CLOSE_STATES}")
    if state in ("retrieved", "refuted"):
        sources = tuple(raw.get("sources") or ())
        require(bool(sources), f"{state} requires at least one source id")
        for sid in sources:
            require(sid in ledger.sources, f"unknown source id: {sid}")
        premise = str(raw.get("premise") or "").strip()
        detail = str(raw.get("detail") or "").strip()
        if state == "retrieved":
            return Retrieved(sources, premise, detail)
        require(bool(premise), "refuted requires the contradicted premise")
        return Refuted(sources, premise, detail)
    if state == "folded":
        into = str(raw.get("into") or "").strip()
        target = ledger.leaves.get(into)
        require(target is not None, f"fold target does not exist: {into}")
        require(
            isinstance(target.state, Retrieved),
            f"fold target must be retrieved: {into}",
        )
        return Folded(into)
    detail = str(raw.get("detail") or "").strip()
    if state == "unresolved":
        reason = raw.get("reason")
        require(
            reason in UNRESOLVED_REASONS,
            f"unresolved reason must be one of {UNRESOLVED_REASONS}",
        )
        require(bool(detail), "unresolved requires detail")
        return Unresolved(reason, detail)
    require(bool(detail), "retired detail must name the conclusion it fails to change")
    return Retired(detail)


def _apply_close(ledger: Ledger, raw: dict[str, Any]) -> None:
    leaf_id = raw.get("leaf")
    leaf = ledger.leaves.get(leaf_id)
    require(leaf is not None, f"unknown leaf id: {leaf_id}")
    new_state = _close_state(raw, ledger)
    legal = isinstance(leaf.state, Open) or (
        isinstance(leaf.state, Retrieved) and isinstance(new_state, Refuted)
    )
    require(
        legal,
        f"illegal transition on {leaf_id}: {type(leaf.state).__name__} -> "
        f"{type(new_state).__name__} (only Open -> any, Retrieved -> Refuted)",
    )
    ledger.leaves[leaf_id] = Leaf(leaf.question, leaf.origin, new_state)


def apply(ledger: Ledger, raw: dict[str, Any]) -> Ledger:
    """Admit one raw event into the ledger, or raise the violated invariant.

    This is the smart constructor: an event this function rejects is never
    appended, so the log on disk holds only admitted events.
    """
    require(ledger.events < MAX_EVENTS, f"event cap reached ({MAX_EVENTS})")
    kind = raw.get("e")
    match kind:
        case "add_leaf":
            leaf_id = str(raw.get("id") or "").strip()
            require(bool(leaf_id), "add_leaf requires an id")
            require(leaf_id not in ledger.leaves, f"duplicate leaf id: {leaf_id}")
            question = str(raw.get("q") or "").strip()
            require(bool(question), "add_leaf requires a question")
            origin = raw.get("origin", "frame")
            require(origin in ORIGINS, f"origin must be one of {ORIGINS}")
            ledger.leaves[leaf_id] = Leaf(question, origin, Open())
        case "add_source":
            source_id = str(raw.get("id") or "").strip()
            require(bool(source_id), "add_source requires an id")
            require(
                source_id not in ledger.sources, f"duplicate source id: {source_id}"
            )
            leaf_id = raw.get("leaf")
            require(leaf_id in ledger.leaves, f"unknown leaf id: {leaf_id}")
            cls = raw.get("cls")
            require(cls in SOURCE_CLASSES, f"cls must be one of {SOURCE_CLASSES}")
            title = str(raw.get("title") or "").strip()
            require(bool(title), "add_source requires a title")
            ledger.sources[source_id] = Source(
                leaf_id, cls, title, str(raw.get("url") or "")
            )
            ledger.source_order.append(source_id)
        case "close":
            _apply_close(ledger, raw)
        case "sweep":
            checked = str(raw.get("checked") or "").strip()
            require(bool(checked), "sweep requires what was checked")
            candidates = list(raw.get("candidates") or [])
            survivors = list(raw.get("survivors") or [])
            require(
                set(survivors) <= set(candidates),
                "sweep survivors must be a subset of candidates",
            )
            ledger.swept = True
        case "checkpoint":
            searches = raw.get("searches")
            require(
                isinstance(searches, int) and searches >= 0,
                "checkpoint requires a non-negative integer search count",
            )
        case _:
            raise CommandError(f"unknown event kind: {kind}")
    ledger.events += 1
    return ledger


def replay(events: list[dict[str, Any]]) -> Ledger:
    """Total over any log the script wrote; a rejection here means tampering."""
    ledger = Ledger()
    for index, raw in enumerate(events, start=1):
        try:
            apply(ledger, raw)
        except CommandError as exc:
            raise CommandError(f"ledger line {index} does not replay: {exc}") from exc
    return ledger
