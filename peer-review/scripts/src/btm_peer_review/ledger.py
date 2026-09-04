"""Event log to ledger value: one total apply(), replay as a left fold.

An event is parsed into its variant before the ledger sees it, so field shape
is pydantic's business and this module keeps only what the ledger knows:
which ids exist and which are taken.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import Field

from btm_corekit import (
    MAX_EVENTS,
    Model,
    NonEmpty,
    Positive,
    Slug,
    parse_model,
    require,
)
from btm_peer_review.constants import Bank, Kind, Severity
from btm_peer_review.state import Claim, Evidenced, Ledger, Objection


class Stamped(Model):
    """The envelope the log adds on append; a staged batch carries none."""

    t: str = ""


class ClaimEvent(Stamped):
    e: Literal["claim"]
    id: Slug
    verbatim: NonEmpty
    page: Positive


class ObjectionEvent(Stamped, Evidenced):
    e: Literal["objection"]
    id: Slug
    kind: Kind
    severity: Severity
    text: NonEmpty
    claim: Slug | None = None
    where: str | None = None
    prior: tuple[str, ...] = ()
    from_: tuple[str, ...] = Field(default=(), alias="from")


class WalkEvent(Stamped):
    e: Literal["walk"]
    bank: Bank
    note: str = ""


class WithdrawEvent(Stamped):
    e: Literal["withdraw"]
    objection: Slug
    reason: str = ""


def apply(ledger: Ledger, event: dict[str, Any]) -> None:
    ledger.events += 1
    require(ledger.events <= MAX_EVENTS, f"ledger exceeds {MAX_EVENTS} events")
    match event.get("e"):
        case "claim":
            claim = parse_model(ClaimEvent, event, "claim event")
            require(claim.id not in ledger.claims, f"claim {claim.id} minted twice")
            ledger.claims[claim.id] = Claim(verbatim=claim.verbatim, page=claim.page)
            ledger.claim_order.append(claim.id)
        case "objection":
            raised = parse_model(ObjectionEvent, event, "objection event")
            require(
                raised.id not in ledger.objections,
                f"objection {raised.id} minted twice",
            )
            require(
                raised.claim is None or raised.claim in ledger.claims,
                f"objection cites unknown claim {raised.claim!r}",
            )
            # Through the decoder: the record holds one law of its own, that
            # prior work belongs to the novelty bank, and it must reach the
            # command channel rather than escape as a traceback.
            ledger.objections[raised.id] = parse_model(
                Objection,
                {
                    "kind": raised.kind,
                    "severity": raised.severity,
                    "text": raised.text,
                    "claim": raised.claim,
                    "where": raised.where,
                    "evidence": raised.evidence,
                    "prior": raised.prior,
                },
                "objection event",
            )
            ledger.objection_order.append(raised.id)
        case "walk":
            walk = parse_model(WalkEvent, event, "walk event")
            ledger.walks[walk.bank] = walk.note
        case "withdraw":
            withdrawn = parse_model(WithdrawEvent, event, "withdraw event")
            require(
                withdrawn.objection in ledger.objections,
                f"withdraw names unknown {withdrawn.objection}",
            )
            ledger.withdrawn[withdrawn.objection] = withdrawn.reason
        case other:
            require(False, f"unknown event kind {other!r} in the ledger")


def replay(events: Iterable[dict[str, Any]]) -> Ledger:
    ledger = Ledger()
    for event in events:
        apply(ledger, event)
    return ledger
