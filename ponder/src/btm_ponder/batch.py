"""The note smart constructor: resolve keyword references, mint ids, expand events."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from collections.abc import Set as AbstractSet
from typing import Any

from btm_corekit import band_signal, eliminate, resolve
from btm_ponder.state import Ledger, require


def _detail_of(raw: dict[str, Any]) -> str:
    """`into` carries a fold target ref; `detail` carries every other reason."""
    key = "into" if raw.get("reason") == "folded" else "detail"
    return str(raw.get(key) or "")


def _resolve_ref(
    ref: str,
    ids: AbstractSet[str],
    kind: str,
    fresh: AbstractSet[str],
    advisories: list[str],
) -> str:
    """Resolve one reference, recording recovery for ids outside `fresh`.

    A keyword match inside `fresh` is the designed path (the full id is
    born in this very batch), so only a match outside it records recovery.
    """
    full, note = eliminate(resolve(ref, ids), ref, kind)
    if note and full not in fresh:
        advisories.append(note)
    return full


def expand_batch(
    ledger: Ledger, batch: dict[str, Any], minter: Callable[[Iterable[str]], str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]], list[str]]:
    """Resolve keyword references and mint ids for one note batch.

    Admission order inside a batch: leaves, sources, closes, sweep,
    checkpoint, so later entries may reference ids minted earlier in the
    same batch. Returns the expanded events, the minted-id maps, and the
    advisory signals for the shell to render.
    """
    known = {"leaves", "sources", "closes", "sweeps", "checkpoints"}
    unknown = set(batch) - known
    require(not unknown, f"unknown note keys: {', '.join(sorted(unknown))}")
    minted: dict[str, dict[str, str]] = {"leaves": {}, "sources": {}}
    advisories: list[str] = []
    fresh: set[str] = set()
    leaf_ids = set(ledger.leaves)
    source_ids = set(ledger.sources)
    events: list[dict[str, Any]] = []

    def admit(kind: str, entry: dict[str, Any], into: set[str]) -> str:
        full = minter(entry.get("kw") or [])
        stem = full.rsplit("-", 1)[0]
        require(
            stem not in minted[kind],
            f"duplicate keywords in one batch: {stem}; vary one keyword",
        )
        minted[kind][stem] = full
        if advice := band_signal(stem):
            advisories.append(advice)
        fresh.add(full)
        into.add(full)
        return full

    for entry in batch.get("leaves") or []:
        full = admit("leaves", entry, leaf_ids)
        events.append(
            {
                "e": "add_leaf",
                "id": full,
                "q": entry.get("q"),
                "origin": entry.get("origin", "frame"),
            }
        )
    for entry in batch.get("sources") or []:
        full = admit("sources", entry, source_ids)
        events.append(
            {
                "e": "add_source",
                "id": full,
                "leaf": _resolve_ref(
                    str(entry.get("leaf") or ""), leaf_ids, "leaf", fresh, advisories
                ),
                "cls": entry.get("cls"),
                "title": entry.get("title"),
                "url": entry.get("url", ""),
            }
        )
    for entry in batch.get("closes") or []:
        event: dict[str, Any] = {
            "e": "close",
            "leaf": _resolve_ref(
                str(entry.get("leaf") or ""), leaf_ids, "leaf", fresh, advisories
            ),
            "state": entry.get("state"),
        }
        if entry.get("sources"):
            event["sources"] = [
                _resolve_ref(str(ref), source_ids, "source", fresh, advisories)
                for ref in entry["sources"]
            ]
        if entry.get("premise"):
            event["premise"] = entry["premise"]
        if entry.get("reason"):
            event["reason"] = entry["reason"]
            detail = _detail_of(entry)
            if entry["reason"] == "folded":
                detail = _resolve_ref(detail, leaf_ids, "leaf", fresh, advisories)
            event["detail"] = detail
        events.append(event)
    for entry in batch.get("sweeps") or []:
        events.append({"e": "sweep", **entry})
    for entry in batch.get("checkpoints") or []:
        events.append({"e": "checkpoint", **entry})
    require(bool(events), "empty note: nothing to record")
    return events, minted, advisories
