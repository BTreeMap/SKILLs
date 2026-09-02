"""The note pipeline: parse, resolve, simulate; a rejection lists every fix at once.

The consuming agent pays output tokens for the batch and pays them again on
every resend, so a rejection must be the last one: every phase runs to
completion, each problem is an imperative corrective order with a hint, and
the ledger changes only when the problem list is empty.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from btm_corekit import Admission, CommandError, Diagnostic, Pool, keywords_of, slugify
from btm_ponder.ledger import apply
from btm_ponder.state import Ledger

BATCH_KEYS = ("leaves", "sources", "closes", "sweeps", "checkpoints")
SCHEMA: dict[str, str] = {
    "leaves": '{"kw": ["two", "words"], "q": "the sub-question", '
    '"origin": "frame|spawned"}',
    "sources": '{"kw": ["two", "words"] or "ref": "explicit-name", "leaf": "<ref>", '
    '"cls": "constitutive|attested|measured|reported", "title": "...", "url": "..."}',
    "closes": '{"leaf": "<ref>", "state": "retrieved|refuted|unresolved|retired", '
    '"sources": ["<ref>"], "premise": "the claim, one line", '
    '"detail": "supporting note; retired: why immaterial", '
    '"reason": "searched|not_pursued (unresolved only)", '
    '"into": "<leaf ref> (folded only)", "from": ["<pad id>"] (optional)}',
    "sweeps": '{"checked": "...", "candidates": ["prose", "..."], '
    '"survivors": [0, 2]} (survivors are zero-based indexes into candidates)',
    "checkpoints": '{"label": "round-1", "searches": 5}',
}


@dataclass(slots=True)
class NoteResult:
    """Everything one batch produced; events commit only when problems is empty."""

    events: list[dict[str, Any]] = field(default_factory=list)
    minted: dict[str, dict[str, str]] = field(
        default_factory=lambda: {"leaves": {}, "sources": {}}
    )
    merged: dict[str, str] = field(default_factory=dict)  # batch stem -> existing id
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)


def _stem(entry: dict[str, Any]) -> str | None:
    words = [entry["ref"]] if entry.get("ref") else entry.get("kw") or []
    try:
        return slugify(words)
    except CommandError:
        return None


def _normal_url(raw: object) -> str:
    return str(raw or "").strip().rstrip("/")


class _Expansion(Admission):
    """One batch working through the phases; every method appends, none raises."""

    def __init__(
        self,
        ledger: Ledger,
        minter: Callable[[Iterable[str]], str],
        pad: Iterable[str],
    ) -> None:
        super().__init__(minter, pad)
        self.ledger = ledger
        self.aliases: dict[str, str] = {}  # merged stems -> existing ids
        self.merged: dict[str, str] = {}
        self.staged: list[tuple[str, dict[str, Any]]] = []
        self.events: list[dict[str, Any]] = []
        self.leaves = Pool("leaf", list(ledger.leaves))
        self.sources = Pool("source", list(ledger.sources))
        self.url_index = {
            _normal_url(source.url): source_id
            for source_id, source in ledger.sources.items()
            if _normal_url(source.url)
        }

    def lookup(self, ref: str, pool: Pool, where: str) -> str | None:
        words = keywords_of(ref)
        alias = self.aliases.get(slugify(words)) if words else None
        return alias or self.resolve_ref(ref, pool, where)

    def admit(self, entry: dict[str, Any], pool: Pool, where: str) -> str | None:
        return self.mint_id(entry, pool, where)

    def take_leaves(self, entries: list[dict[str, Any]]) -> None:
        for index, entry in enumerate(entries):
            where = f"leaves[{index}]"
            full = self.admit(entry, self.leaves, where)
            if full is None:
                continue
            self.staged.append(
                (
                    where,
                    {
                        "e": "add_leaf",
                        "id": full,
                        "q": entry.get("q"),
                        "origin": entry.get("origin", "frame"),
                    },
                )
            )

    def take_sources(self, entries: list[dict[str, Any]]) -> None:
        for index, entry in enumerate(entries):
            where = f"sources[{index}]"
            url = _normal_url(entry.get("url"))
            stem = _stem(entry)
            if url and url in self.url_index and stem is not None:
                existing = self.url_index[url]
                self.merged[stem] = existing
                self.aliases[stem] = existing
                self.advisories.append(
                    f"{where} merges into {existing}: same url already in the ledger"
                )
                continue
            full = self.admit(entry, self.sources, where)
            if full is None:
                continue
            leaf = self.lookup(
                str(entry.get("leaf") or ""), self.leaves, f"{where}.leaf"
            )
            if leaf is None:
                continue
            if url:
                self.url_index[url] = full
            self.staged.append(
                (
                    where,
                    {
                        "e": "add_source",
                        "id": full,
                        "leaf": leaf,
                        "cls": entry.get("cls"),
                        "title": entry.get("title"),
                        "url": str(entry.get("url") or ""),
                    },
                )
            )

    def take_closes(self, entries: list[dict[str, Any]]) -> None:
        for index, entry in enumerate(entries):
            where = f"closes[{index}]"
            leaf = self.lookup(
                str(entry.get("leaf") or ""), self.leaves, f"{where}.leaf"
            )
            links = self.links(entry, where)
            broken = leaf is None or links is None
            event: dict[str, Any] = {
                "e": "close",
                "leaf": leaf,
                "state": entry.get("state"),
                "from": list(links or ()),
            }
            if entry.get("sources"):
                resolved = [
                    self.lookup(str(ref), self.sources, f"{where}.sources[{j}]")
                    for j, ref in enumerate(entry["sources"])
                ]
                broken = broken or None in resolved
                event["sources"] = resolved
            if entry.get("premise"):
                event["premise"] = entry["premise"]
            if entry.get("reason"):
                event["reason"] = entry["reason"]
            if entry.get("detail"):
                event["detail"] = entry["detail"]
            if entry.get("state") == "folded" or entry.get("into"):
                into = self.lookup(
                    str(entry.get("into") or ""), self.leaves, f"{where}.into"
                )
                broken = broken or into is None
                event["into"] = into
            if not broken:
                self.staged.append((where, event))

    def take_sweeps(self, entries: list[dict[str, Any]]) -> None:
        for index, entry in enumerate(entries):
            where = f"sweeps[{index}]"
            candidates = list(entry.get("candidates") or [])
            survivors = self._survivors(entry, candidates, where)
            if survivors is None:
                continue
            self.staged.append(
                (
                    where,
                    {
                        "e": "sweep",
                        "checked": entry.get("checked"),
                        "candidates": candidates,
                        "survivors": survivors,
                    },
                )
            )

    def _survivors(
        self, entry: dict[str, Any], candidates: list[str], where: str
    ) -> list[str] | None:
        chosen: list[str] = []
        broken = False
        for j, survivor in enumerate(entry.get("survivors") or []):
            spot = f"{where}.survivors[{j}]"
            if isinstance(survivor, int):
                if 0 <= survivor < len(candidates):
                    chosen.append(candidates[survivor])
                else:
                    self.fail(
                        spot,
                        f"index {survivor} is out of range: candidates has "
                        f"{len(candidates)} entries",
                        hint="survivors are zero-based indexes into candidates",
                    )
                    broken = True
            elif survivor in candidates:
                chosen.append(survivor)
            else:
                self.fail(
                    spot,
                    f"replace '{survivor}': it does not appear verbatim in candidates",
                    hint='write zero-based indexes instead: "survivors": [0]',
                )
                broken = True
        return None if broken else chosen

    def take_checkpoints(self, entries: list[dict[str, Any]]) -> None:
        for index, entry in enumerate(entries):
            self.staged.append((f"checkpoints[{index}]", {"e": "checkpoint", **entry}))

    def simulate(self) -> None:
        """Replay staged events on the ledger, turning refusals into orders."""
        for where, event in self.staged:
            try:
                apply(self.ledger, event)
            except CommandError as exc:
                kind = where.split("[", 1)[0]
                self.fail(where, str(exc), hint=SCHEMA.get(kind))
            else:
                self.events.append(event)


def expand_batch(
    ledger: Ledger,
    batch: dict[str, Any],
    minter: Callable[[Iterable[str]], str],
    pad: Iterable[str] = (),
) -> NoteResult:
    """Expand one note batch into events, collecting every problem.

    Admission order: leaves, sources, closes, sweeps, checkpoints, so later
    entries may reference ids minted earlier in the batch. Events from clean
    entries are simulated against the passed ledger (which is mutated); on a
    non-empty problem list the caller discards ledger and events alike.
    """
    expansion = _Expansion(ledger, minter, pad)
    expansion.keys(batch, BATCH_KEYS)
    expansion.take_leaves(batch.get("leaves") or [])
    expansion.take_sources(batch.get("sources") or [])
    expansion.take_closes(batch.get("closes") or [])
    expansion.take_sweeps(batch.get("sweeps") or [])
    expansion.take_checkpoints(batch.get("checkpoints") or [])
    if not expansion.staged and expansion.clean:
        expansion.fail("$", "add at least one entry: the batch records nothing")
    expansion.simulate()
    return NoteResult(
        events=expansion.events,
        minted={
            "leaves": expansion.leaves.minted,
            "sources": expansion.sources.minted,
        },
        merged=expansion.merged,
        advisories=expansion.advisories,
        problems=expansion.problems,
    )
