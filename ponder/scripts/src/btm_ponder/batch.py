"""The note pipeline: parse, resolve, simulate; a rejection lists every fix at once.

The agent pays output tokens for the batch and again on every resend, so
every phase runs to completion and the ledger changes only when the problem
list comes back empty.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import ConfigDict, Field

from btm_corekit import (
    Admission,
    CommandError,
    Diagnostic,
    Model,
    Named,
    NonEmpty,
    Pool,
    dump,
    keywords_of,
    slugify,
)
from btm_ponder.ledger import apply
from btm_ponder.state import (
    Checkpoint,
    CloseState,
    Ledger,
    Origin,
    Reason,
    SourceClass,
)

SCHEMA: dict[str, str] = {
    "leaves": '{"kw": ["two", "words"], "q": "the sub-question", '
    '"origin": "frame|spawned"}',
    "sources": '{"kw": ["two", "words"] or "ref": "explicit-name", "leaf": "<ref>", '
    '"cls": "constitutive|attested|measured|reported", "title": "...", "url": "..."}',
    "closes": '{"leaf": "<ref>", '
    '"state": "retrieved|refuted|unresolved|retired|folded", '
    '"sources": ["<ref>"], "premise": "the claim, one line", '
    '"detail": "supporting note; retired: why immaterial", '
    '"reason": "searched|not_pursued (unresolved only)", '
    '"into": "<leaf ref> (folded only)", "from": ["<pad id>"] (optional)}',
    "sweeps": '{"checked": "...", "candidates": ["prose", "..."], '
    '"survivors": [0, 2]} (survivors are zero-based indexes into candidates)',
    "checkpoints": '{"label": "round-1", "searches": 5}',
}


class LeafEntry(Named):
    q: NonEmpty
    origin: Origin = Origin.FRAME


class SourceEntry(Named):
    leaf: NonEmpty
    cls: SourceClass
    title: NonEmpty
    url: str = ""


class CloseEntry(Model):
    """References are unresolved here; which fields each state needs is the
    event's law, reported when the close is simulated."""

    leaf: NonEmpty
    state: CloseState
    sources: tuple[NonEmpty, ...] = ()
    premise: str = ""
    detail: str = ""
    reason: Reason | None = None
    into: str | None = None
    from_: tuple[str, ...] = Field(default=(), alias="from")


class SweepEntry(Model):
    checked: NonEmpty
    candidates: tuple[str, ...] = ()
    survivors: tuple[int | str, ...] = ()


Rows = tuple[Mapping[str, Any], ...]


class NoteBatch(Model):
    """The container. Rows stay opaque here and decode one at a time, so a
    row with a bad field still lets its neighbours resolve. Extras are named
    by `known_keys`, so one unknown key cannot swallow the whole batch."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    leaves: Rows = ()
    sources: Rows = ()
    closes: Rows = ()
    sweeps: Rows = ()
    checkpoints: Rows = ()


BATCH_KEYS = tuple(NoteBatch.model_fields)


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


def _stem(entry: Named) -> str | None:
    try:
        return slugify(entry.words)
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

    def take_leaves(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"leaves[{index}]"
            entry = self.decode(LeafEntry, row, where, SCHEMA["leaves"])
            if entry is None:
                continue
            full = self.mint_id(entry, self.leaves, where)
            if full is None:
                continue
            self.staged.append(
                (
                    where,
                    {
                        "e": "add_leaf",
                        "id": full,
                        "q": entry.q,
                        "origin": entry.origin,
                    },
                )
            )

    def take_sources(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"sources[{index}]"
            entry = self.decode(SourceEntry, row, where, SCHEMA["sources"])
            if entry is None:
                continue
            url = _normal_url(entry.url)
            stem = _stem(entry)
            if url and url in self.url_index and stem is not None:
                existing = self.url_index[url]
                self.merged[stem] = existing
                self.aliases[stem] = existing
                self.advisories.append(
                    f"{where} merges into {existing}: same url already in the ledger"
                )
                continue
            full = self.mint_id(entry, self.sources, where)
            if full is None:
                continue
            leaf = self.lookup(entry.leaf, self.leaves, f"{where}.leaf")
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
                        "cls": entry.cls,
                        "title": entry.title,
                        "url": entry.url,
                    },
                )
            )

    def take_closes(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"closes[{index}]"
            entry = self.decode(CloseEntry, row, where, SCHEMA["closes"])
            if entry is None:
                continue
            leaf = self.lookup(entry.leaf, self.leaves, f"{where}.leaf")
            broken = leaf is None or not self.pad_links(entry.from_, where)
            event: dict[str, Any] = {
                "e": "close",
                "leaf": leaf,
                "state": entry.state,
                "from": list(entry.from_),
            }
            if entry.sources:
                resolved = [
                    self.lookup(ref, self.sources, f"{where}.sources[{position}]")
                    for position, ref in enumerate(entry.sources)
                ]
                broken = broken or None in resolved
                event["sources"] = resolved
            if entry.premise:
                event["premise"] = entry.premise
            if entry.reason:
                event["reason"] = entry.reason
            if entry.detail:
                event["detail"] = entry.detail
            if entry.state is CloseState.FOLDED or entry.into:
                into = self.lookup(entry.into or "", self.leaves, f"{where}.into")
                broken = broken or into is None
                event["into"] = into
            if not broken:
                self.staged.append((where, event))

    def take_sweeps(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"sweeps[{index}]"
            entry = self.decode(SweepEntry, row, where, SCHEMA["sweeps"])
            if entry is None:
                continue
            candidates = list(entry.candidates)
            survivors = self._survivors(entry.survivors, candidates, where)
            if survivors is None:
                continue
            self.staged.append(
                (
                    where,
                    {
                        "e": "sweep",
                        "checked": entry.checked,
                        "candidates": candidates,
                        "survivors": survivors,
                    },
                )
            )

    def _survivors(
        self, survivors: tuple[int | str, ...], candidates: list[str], where: str
    ) -> list[str] | None:
        chosen: list[str] = []
        broken = False
        for j, survivor in enumerate(survivors):
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

    def take_checkpoints(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"checkpoints[{index}]"
            checkpoint = self.decode(Checkpoint, row, where, SCHEMA["checkpoints"])
            if checkpoint is None:
                continue
            # Through the model, so no entry key can reach the event and
            # overwrite `e` with a kind that mints nothing.
            self.staged.append((where, {"e": "checkpoint", **dump(checkpoint)}))

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
    expansion.known_keys(batch, NoteBatch)
    note = expansion.decode(NoteBatch, batch)
    if note is not None:
        expansion.take_leaves(note.leaves)
        expansion.take_sources(note.sources)
        expansion.take_closes(note.closes)
        expansion.take_sweeps(note.sweeps)
        expansion.take_checkpoints(note.checkpoints)
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
