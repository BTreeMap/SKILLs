"""Event transitions: the smart constructor that decides what the log may hold."""

from __future__ import annotations

from typing import Any

from btm_corekit import (
    MAX_EVENTS,
    CommandError,
    demand,
    parse_enum,
    parse_model,
    read_text,
    require,
)
from btm_ponder.state import (
    CLOSE_STATES,
    Folded,
    Leaf,
    LeafState,
    Ledger,
    Open,
    Origin,
    Reason,
    Refuted,
    Retired,
    Retrieved,
    Source,
    SourceClass,
    Sweep,
    Unresolved,
)


def _sweep(raw: dict[str, Any]) -> Sweep:
    """The record the draft cites, not the bit that a sweep happened."""
    return parse_model(
        Sweep,
        {
            "checked": raw.get("checked"),
            "candidates": tuple(raw.get("candidates") or ()),
            "survivors": tuple(raw.get("survivors") or ()),
        },
        "sweep event",
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
            return Retrieved(sources=sources, premise=premise, detail=detail)
        require(bool(premise), "refuted requires the contradicted premise")
        return Refuted(sources=sources, premise=premise, detail=detail)
    if state == "folded":
        into = str(raw.get("into") or "").strip()
        target = demand(ledger.leaves.get(into), f"fold target does not exist: {into}")
        require(
            isinstance(target.state, Retrieved),
            f"fold target must be retrieved: {into}",
        )
        return Folded(into=into)
    detail = str(raw.get("detail") or "").strip()
    if state == "unresolved":
        require(bool(detail), "unresolved requires detail")
        return Unresolved(
            reason=parse_enum(Reason, raw.get("reason"), "unresolved reason"),
            detail=detail,
        )
    require(bool(detail), "retired detail must name the conclusion it fails to change")
    return Retired(detail=detail)


def _apply_close(ledger: Ledger, raw: dict[str, Any]) -> None:
    leaf_id = read_text(raw, "leaf", "close")
    leaf = demand(ledger.leaves.get(leaf_id), f"unknown leaf id: {leaf_id}")
    new_state = _close_state(raw, ledger)
    legal = isinstance(leaf.state, Open) or (
        isinstance(leaf.state, Retrieved) and isinstance(new_state, Refuted)
    )
    require(
        legal,
        f"illegal transition on {leaf_id}: {type(leaf.state).__name__} -> "
        f"{type(new_state).__name__} (only Open -> any, Retrieved -> Refuted)",
    )
    ledger.leaves[leaf_id] = Leaf(
        question=leaf.question, origin=leaf.origin, state=new_state
    )


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
            origin = parse_enum(Origin, origin, "leaf origin")
            ledger.leaves[leaf_id] = Leaf(
                question=question, origin=origin, state=Open()
            )
        case "add_source":
            source_id = str(raw.get("id") or "").strip()
            require(bool(source_id), "add_source requires an id")
            require(
                source_id not in ledger.sources, f"duplicate source id: {source_id}"
            )
            leaf_id = read_text(raw, "leaf", "add_source")
            require(leaf_id in ledger.leaves, f"unknown leaf id: {leaf_id}")
            cls = raw.get("cls")
            cls = parse_enum(SourceClass, cls, "source cls")
            title = str(raw.get("title") or "").strip()
            require(bool(title), "add_source requires a title")
            ledger.sources[source_id] = Source(
                leaf=leaf_id, cls=cls, title=title, url=str(raw.get("url") or "")
            )
            ledger.source_order.append(source_id)
        case "close":
            _apply_close(ledger, raw)
        case "sweep":
            ledger.sweeps.append(_sweep(raw))
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
