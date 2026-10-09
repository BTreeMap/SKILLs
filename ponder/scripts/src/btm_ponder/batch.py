"""The record pipeline: parse, resolve, simulate; a rejection lists every fix at once.

The agent pays output tokens for the batch and again on every resend, so
every phase runs to completion and the ledger changes only when the problem
list comes back empty.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any

from pydantic import BeforeValidator, ConfigDict, Field

from btm_corekit import (
    Acceptance,
    CommandError,
    Diagnostic,
    Model,
    Named,
    NonEmpty,
    Pool,
    ascii_words,
    dump,
    normalize_arxiv_id,
    normalize_doi,
    slugify,
)
from btm_ponder.ledger import apply
from btm_ponder.state import (
    Checkpoint,
    CloseStatus,
    Ledger,
    Origin,
    Reason,
    SourceClass,
)

SCHEMA: dict[str, str] = {
    "leaves": '{"kw": ["two", "words"], "q": "the sub-question", '
    '"origin": "frame|spawned"}',
    "sources": '{"kw": ["two", "words"] or "ref": "explicit-name", "leaf": "<ref>", '
    '"cls": "constitutive|attested|measured|reported", "title": "...", '
    '"url": "...", "doi": "...", "arxiv": "..." (url, doi, arxiv: any of them; '
    "authors, year, venue optional, copied from a cite record)}",
    "closes": '{"leaf": "<ref>", '
    '"status": "retrieved|refuted|unresolved|retired|folded", '
    '"sources": ["<ref>"], "premise": "the claim, one line", '
    '"detail": "supporting note; retired: why immaterial", '
    '"reason": "found|not_pursued (unresolved only)", '
    '"into": "<leaf ref> (folded only)", "from": ["<pad id>"] (optional)}',
    "scans": '{"checked": "...", "candidates": ["prose", "..."], '
    '"survivors": [0, 2]} (survivors are zero-based indexes into candidates)',
    "checkpoints": '{"label": "cycle-1", "queries": 5}',
}


class LeafEntry(Named):
    q: NonEmpty
    origin: Origin = Origin.FRAME


def _identifier(normalize: Callable[[Any], Any], what: str) -> BeforeValidator:
    """The bare form of an identifier the agent wrote in any spelling the
    normalizer reads; one it cannot read is a rejection, never a silent drop."""

    def bare(raw: Any) -> Any:
        if raw is None:
            return None
        found = normalize(raw)
        if found is None:
            raise ValueError(f"{raw!r} is no {what}; write it bare or drop it")
        return found

    return BeforeValidator(bare)


class SourceEntry(Named):
    leaf: NonEmpty
    cls: SourceClass
    title: NonEmpty
    url: str = ""
    doi: Annotated[str | None, _identifier(normalize_doi, "DOI")] = None
    arxiv: Annotated[str | None, _identifier(normalize_arxiv_id, "arXiv id")] = None
    authors: tuple[NonEmpty, ...] = ()
    year: int | None = None
    venue: NonEmpty | None = None

    @property
    def address(self) -> str:
        """The url as given, else the DOI's or arXiv id's landing page, so a
        source recorded by identifier dedups against one recorded by its link."""
        if self.url:
            return self.url
        if self.doi:
            return f"https://doi.org/{self.doi}"
        return f"https://arxiv.org/abs/{self.arxiv}" if self.arxiv else ""


class CloseEntry(Model):
    """References are unresolved here; which fields each status needs is the
    event's law, reported when the close is simulated."""

    leaf: NonEmpty
    status: CloseStatus
    sources: tuple[NonEmpty, ...] = ()
    premise: str = ""
    detail: str = ""
    reason: Reason | None = None
    into: str | None = None
    from_: tuple[str, ...] = Field(default=(), alias="from")


class ScanEntry(Model):
    checked: NonEmpty
    candidates: tuple[str, ...] = ()
    survivors: tuple[int | str, ...] = ()


Rows = tuple[Mapping[str, Any], ...]


class RecordBatch(Model):
    """The container. Rows stay opaque here and decode one at a time, so a
    row with a bad field still lets its neighbours resolve. Extras are named
    by `known_keys`, so one unknown key cannot swallow the whole batch."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    leaves: Rows = ()
    sources: Rows = ()
    closes: Rows = ()
    scans: Rows = ()
    checkpoints: Rows = ()


BATCH_KEYS = tuple(RecordBatch.model_fields)


@dataclass(slots=True)
class RecordResult:
    """Everything one batch produced; events commit only when problems is empty."""

    events: list[dict[str, Any]] = field(default_factory=list)
    new: dict[str, dict[str, str]] = field(
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


def cited_fields(entry: SourceEntry) -> dict[str, Any]:
    """The citation fields the entry carries, absent ones left off so an
    event without them reads as it did before they existed."""
    given = {
        "doi": entry.doi,
        "arxiv_id": entry.arxiv,
        "authors": list(entry.authors),
        "year": entry.year,
        "venue": entry.venue,
    }
    return {key: value for key, value in given.items() if value}


def _normal_url(raw: object) -> str:
    return str(raw or "").strip().rstrip("/")


class _Expansion(Acceptance):
    """One batch working through the phases; every method appends, none raises."""

    def __init__(
        self,
        ledger: Ledger,
        maker: Callable[[Iterable[str]], str],
        pad: Iterable[str],
    ) -> None:
        super().__init__(maker, pad)
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
        words = ascii_words(ref)
        alias = self.aliases.get(slugify(words)) if words else None
        return alias or self.resolve_ref(ref, pool, where)

    def take_leaves(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"leaves[{index}]"
            entry = self.decode(LeafEntry, row, where, SCHEMA["leaves"])
            if entry is None:
                continue
            full = self.make_id(entry, self.leaves, where)
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
            url = _normal_url(entry.address)
            stem = _stem(entry)
            if url and url in self.url_index and stem is not None:
                existing = self.url_index[url]
                self.merged[stem] = existing
                self.aliases[stem] = existing
                self.advisories.append(
                    f"{where} merges into {existing}: same url already in the ledger"
                )
                continue
            full = self.make_id(entry, self.sources, where)
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
                        "url": entry.address,
                        **cited_fields(entry),
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
            # Both checks run: `or` would skip the pad links whenever the leaf
            # ref is the problem, hiding a bad pad id until the next resend.
            pad_ok = self.pad_links(entry.from_, where)
            broken = leaf is None or not pad_ok
            event: dict[str, Any] = {
                "e": "close",
                "leaf": leaf,
                "status": entry.status,
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
            if entry.status is CloseStatus.FOLDED or entry.into:
                into = self.lookup(entry.into or "", self.leaves, f"{where}.into")
                broken = broken or into is None
                event["into"] = into
            if not broken:
                self.staged.append((where, event))

    def take_scans(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"scans[{index}]"
            entry = self.decode(ScanEntry, row, where, SCHEMA["scans"])
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
                        "e": "scan",
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
            # overwrite `e` with a kind that makes nothing.
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
    maker: Callable[[Iterable[str]], str],
    pad: Iterable[str] = (),
) -> RecordResult:
    """Expand one record batch into events, collecting every problem.

    Acceptance order: leaves, sources, closes, scans, checkpoints, so later
    entries may reference ids made earlier in the batch. Events from clean
    entries are simulated against the passed ledger (which is mutated); on a
    non-empty problem list the caller discards ledger and events alike.
    """
    expansion = _Expansion(ledger, maker, pad)
    expansion.known_keys(batch, RecordBatch)
    record = expansion.families(batch, RecordBatch, SCHEMA)
    expansion.take_leaves(record.leaves)
    expansion.take_sources(record.sources)
    expansion.take_closes(record.closes)
    expansion.take_scans(record.scans)
    expansion.take_checkpoints(record.checkpoints)
    if not expansion.staged and expansion.clean:
        expansion.fail("$", "add at least one entry: the batch records nothing")
    expansion.simulate()
    return RecordResult(
        events=expansion.events,
        new={
            "leaves": expansion.leaves.new,
            "sources": expansion.sources.new,
        },
        merged=expansion.merged,
        advisories=expansion.advisories,
        problems=expansion.problems,
    )
