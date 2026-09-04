"""Event log to ledger value: one total apply(), replay as a left fold."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from btm_corekit import MAX_EVENTS, parse_enum, read_text, require
from btm_peer_review.constants import Bank
from btm_peer_review.state import Ledger, claim_from_event, objection_from_event


def apply(ledger: Ledger, event: dict[str, Any]) -> None:
    ledger.events += 1
    require(ledger.events <= MAX_EVENTS, f"ledger exceeds {MAX_EVENTS} events")
    match event.get("e"):
        case "claim":
            cid = read_text(event, "id", "event")
            require(cid not in ledger.claims, f"claim {cid} minted twice")
            ledger.claims[cid] = claim_from_event(event)
            ledger.claim_order.append(cid)
        case "objection":
            oid = read_text(event, "id", "event")
            require(oid not in ledger.objections, f"objection {oid} minted twice")
            ledger.objections[oid] = objection_from_event(event, ledger.claims)
            ledger.objection_order.append(oid)
        case "walk":
            bank = parse_enum(Bank, event.get("bank"), "walk bank")
            ledger.walks[bank] = str(event.get("note") or "")
        case "withdraw":
            oid = read_text(event, "objection", "event")
            require(oid in ledger.objections, f"withdraw names unknown {oid}")
            ledger.withdrawn[oid] = str(event.get("reason") or "")
        case other:
            require(False, f"unknown event kind {other!r} in the ledger")


def replay(events: Iterable[dict[str, Any]]) -> Ledger:
    ledger = Ledger()
    for event in events:
        apply(ledger, event)
    return ledger
