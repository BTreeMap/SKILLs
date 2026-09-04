"""Event transitions: the smart constructor that decides what the log may hold.

An event is parsed into its variant before the ledger sees it, so field shape
is pydantic's business and this module keeps only what the ledger knows:
which ids exist, which are taken, and which transitions are legal.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter

from btm_corekit import (
    MAX_EVENTS,
    CommandError,
    Model,
    NonEmpty,
    Slug,
    Trimmed,
    demand,
    parse_model,
    parse_with,
    require,
)
from btm_ponder.state import (
    Checkpoint,
    CloseState,
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

Prose = Annotated[str, Trimmed]


class Stamped(Model):
    """The envelope the log adds on append; a staged batch carries none."""

    t: str = ""


class AddLeaf(Stamped):
    e: Literal["add_leaf"]
    id: Slug
    q: NonEmpty
    origin: Origin = Origin.FRAME


class AddSource(Stamped):
    e: Literal["add_source"]
    id: Slug
    leaf: Slug
    cls: SourceClass
    title: NonEmpty
    url: str = ""


class Closing(Stamped):
    """What every close carries; the state decides the rest."""

    e: Literal["close"]
    leaf: Slug
    from_: tuple[str, ...] = Field(default=(), alias="from")


class RetrievedClose(Closing):
    state: Literal[CloseState.RETRIEVED]
    sources: tuple[Slug, ...] = Field(min_length=1)
    premise: Prose = ""
    detail: Prose = ""


class RefutedClose(Closing):
    state: Literal[CloseState.REFUTED]
    sources: tuple[Slug, ...] = Field(min_length=1)
    premise: NonEmpty
    detail: Prose = ""


class UnresolvedClose(Closing):
    state: Literal[CloseState.UNRESOLVED]
    reason: Reason
    detail: NonEmpty


class RetiredClose(Closing):
    state: Literal[CloseState.RETIRED]
    detail: NonEmpty


class FoldedClose(Closing):
    state: Literal[CloseState.FOLDED]
    into: Slug


def _legacy_fold(raw: Any) -> Any:
    """Logs written before `folded` became a state spell it as a retired close
    whose reason is folded."""
    if not isinstance(raw, dict) or raw.get("state") != CloseState.RETIRED:
        return raw
    if raw.get("reason") != "folded":
        return raw
    lifted = {k: v for k, v in raw.items() if k not in ("reason", "detail")}
    return {
        **lifted,
        "state": CloseState.FOLDED,
        "into": raw.get("into") or raw.get("detail"),
    }


CloseEvent = (
    RetrievedClose | RefutedClose | UnresolvedClose | RetiredClose | FoldedClose
)
CLOSE: TypeAdapter[CloseEvent] = TypeAdapter(
    Annotated[CloseEvent, Field(discriminator="state")]
)


# A projection names every field it reads, so the envelope cannot smuggle
# one in; the record it builds owns its own law.
def _sweep(raw: dict[str, Any]) -> Sweep:
    return parse_model(
        Sweep,
        {
            "checked": raw.get("checked"),
            "candidates": tuple(raw.get("candidates") or ()),
            "survivors": tuple(raw.get("survivors") or ()),
        },
        "sweep event",
    )


def _checkpoint(raw: dict[str, Any]) -> Checkpoint:
    return parse_model(
        Checkpoint,
        {"label": raw.get("label", ""), "searches": raw.get("searches")},
        "checkpoint event",
    )


def _known(sources: tuple[str, ...], ledger: Ledger) -> None:
    for source_id in sources:
        require(source_id in ledger.sources, f"unknown source id: {source_id}")


def _state_of(event: CloseEvent, ledger: Ledger) -> LeafState:
    """The variant this close names. Shape is already parsed; what is checked
    here is what only the ledger knows."""
    match event:
        case RetrievedClose(sources=sources, premise=premise, detail=detail):
            _known(sources, ledger)
            return Retrieved(sources=sources, premise=premise, detail=detail)
        case RefutedClose(sources=sources, premise=premise, detail=detail):
            _known(sources, ledger)
            return Refuted(sources=sources, premise=premise, detail=detail)
        case UnresolvedClose(reason=reason, detail=detail):
            return Unresolved(reason=reason, detail=detail)
        case RetiredClose(detail=detail):
            return Retired(detail=detail)
        case FoldedClose(into=into):
            target = demand(
                ledger.leaves.get(into), f"fold target does not exist: {into}"
            )
            require(
                isinstance(target.state, Retrieved),
                f"fold target must be retrieved: {into}",
            )
            return Folded(into=into)


def _apply_close(ledger: Ledger, raw: dict[str, Any]) -> None:
    event = parse_with(CLOSE, _legacy_fold(raw), "close event")
    leaf = demand(ledger.leaves.get(event.leaf), f"unknown leaf id: {event.leaf}")
    new_state = _state_of(event, ledger)
    legal = isinstance(leaf.state, Open) or (
        isinstance(leaf.state, Retrieved) and isinstance(new_state, Refuted)
    )
    require(
        legal,
        f"illegal transition on {event.leaf}: {type(leaf.state).__name__} -> "
        f"{type(new_state).__name__} (only Open -> any, Retrieved -> Refuted)",
    )
    ledger.leaves[event.leaf] = Leaf(
        question=leaf.question, origin=leaf.origin, state=new_state
    )


def apply(ledger: Ledger, raw: dict[str, Any]) -> Ledger:
    """Admit one raw event into the ledger, or raise the violated invariant.

    This is the smart constructor: an event this function rejects is never
    appended, so the log on disk holds only admitted events.
    """
    require(ledger.events < MAX_EVENTS, f"event cap reached ({MAX_EVENTS})")
    match raw.get("e"):
        case "add_leaf":
            event = parse_model(AddLeaf, raw, "add_leaf event")
            require(event.id not in ledger.leaves, f"duplicate leaf id: {event.id}")
            ledger.leaves[event.id] = Leaf(
                question=event.q, origin=event.origin, state=Open()
            )
        case "add_source":
            source = parse_model(AddSource, raw, "add_source event")
            require(
                source.id not in ledger.sources, f"duplicate source id: {source.id}"
            )
            require(source.leaf in ledger.leaves, f"unknown leaf id: {source.leaf}")
            ledger.sources[source.id] = Source(
                leaf=source.leaf, cls=source.cls, title=source.title, url=source.url
            )
            ledger.source_order.append(source.id)
        case "close":
            _apply_close(ledger, raw)
        case "sweep":
            ledger.sweeps.append(_sweep(raw))
        case "checkpoint":
            _checkpoint(raw)
        case kind:
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
