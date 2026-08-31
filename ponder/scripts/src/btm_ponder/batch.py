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

from btm_corekit import (
    Ambiguous,
    CommandError,
    Diagnostic,
    Exact,
    NoMatch,
    Recovered,
    band_signal,
    keywords_of,
    resolve,
    slugify,
)
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
    '"into": "<leaf ref> (folded only)"}',
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


def near_misses(ref: str, ids: Iterable[str]) -> list[str]:
    """Ids sharing keywords with a failed reference, best overlap first."""
    words = set(keywords_of(ref))
    scored = sorted(
        ((len(words & set(keywords_of(candidate))), candidate) for candidate in ids),
        key=lambda pair: (-pair[0], pair[1]),
    )
    return [candidate for overlap, candidate in scored if overlap > 0][:3]


def _safe_slug(entry: dict[str, Any]) -> str | None:
    words = [entry["ref"]] if entry.get("ref") else entry.get("kw") or []
    try:
        return slugify(words)
    except CommandError:
        return None


def _normal_url(raw: object) -> str:
    return str(raw or "").strip().rstrip("/")


@dataclass(slots=True)
class _Expansion:
    """One batch working through the phases; every method appends, none raises."""

    ledger: Ledger
    minter: Callable[[Iterable[str]], str]
    result: NoteResult = field(default_factory=NoteResult)
    aliases: dict[str, str] = field(default_factory=dict)  # merged stems -> ids
    fresh: set[str] = field(default_factory=set)
    staged: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    leaf_ids: set[str] = field(init=False)
    source_ids: set[str] = field(init=False)
    url_index: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        self.leaf_ids = set(self.ledger.leaves)
        self.source_ids = set(self.ledger.sources)
        self.url_index = {
            _normal_url(source.url): source_id
            for source_id, source in self.ledger.sources.items()
            if _normal_url(source.url)
        }

    def problem(self, where: str, fix: str, hint: str | None = None) -> None:
        self.result.problems.append(Diagnostic(where, fix, hint))

    def lookup(self, ref: str, ids: set[str], kind: str, where: str) -> str | None:
        words = keywords_of(ref)
        alias = self.aliases.get(slugify(words)) if words else None
        if alias:
            return alias
        match resolve(ref, ids):
            case Exact(full):
                return full
            case Recovered(full):
                if full not in self.fresh:
                    self.result.advisories.append(
                        f"recovered {kind} '{ref}' -> {full}; use the full identifier"
                    )
                return full
            case Ambiguous(candidates):
                self.problem(
                    where,
                    f"replace '{ref}': it matches several {kind}s",
                    hint=f"write one of: {', '.join(candidates)}",
                )
            case NoMatch():
                near = near_misses(ref, ids)
                self.problem(
                    where,
                    f"replace '{ref}': no {kind} matches it",
                    hint=f"did you mean: {', '.join(near)}"
                    if near
                    else f"declare the {kind} earlier in this batch or fix the "
                    "spelling",
                )
        return None

    def admit(
        self, kind: str, entry: dict[str, Any], into: set[str], where: str
    ) -> str | None:
        stem = _safe_slug(entry)
        if stem is None:
            self.problem(
                where,
                "give this entry keywords with letters or digits",
                hint=SCHEMA[kind],
            )
            return None
        if stem in self.result.minted[kind]:
            self.problem(
                where, f"vary one keyword: '{stem}' already minted in this batch"
            )
            return None
        full = self.minter([stem])
        self.result.minted[kind][stem] = full
        if advice := band_signal(stem):
            self.result.advisories.append(advice)
        self.fresh.add(full)
        into.add(full)
        return full

    def take_keys(self, batch: dict[str, Any]) -> None:
        for key in batch:
            if key not in BATCH_KEYS:
                self.problem(
                    key,
                    f"remove or rename the unknown key '{key}'",
                    hint=f"valid keys: {', '.join(BATCH_KEYS)}",
                )

    def take_leaves(self, entries: list[dict[str, Any]]) -> None:
        for index, entry in enumerate(entries):
            where = f"leaves[{index}]"
            full = self.admit("leaves", entry, self.leaf_ids, where)
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
            stem = _safe_slug(entry)
            if url and url in self.url_index and stem is not None:
                existing = self.url_index[url]
                self.result.merged[stem] = existing
                self.aliases[stem] = existing
                self.result.advisories.append(
                    f"{where} merges into {existing}: same url already in the ledger"
                )
                continue
            full = self.admit("sources", entry, self.source_ids, where)
            if full is None:
                continue
            leaf = self.lookup(
                str(entry.get("leaf") or ""), self.leaf_ids, "leaf", f"{where}.leaf"
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
                str(entry.get("leaf") or ""), self.leaf_ids, "leaf", f"{where}.leaf"
            )
            broken = leaf is None
            event: dict[str, Any] = {
                "e": "close",
                "leaf": leaf,
                "state": entry.get("state"),
            }
            if entry.get("sources"):
                resolved = [
                    self.lookup(
                        str(ref), self.source_ids, "source", f"{where}.sources[{j}]"
                    )
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
                    str(entry.get("into") or ""), self.leaf_ids, "leaf", f"{where}.into"
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
                    self.problem(
                        spot,
                        f"index {survivor} is out of range: candidates has "
                        f"{len(candidates)} entries",
                        hint="survivors are zero-based indexes into candidates",
                    )
                    broken = True
            elif survivor in candidates:
                chosen.append(survivor)
            else:
                self.problem(
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
                self.problem(where, str(exc), hint=SCHEMA.get(kind))
            else:
                self.result.events.append(event)


def expand_batch(
    ledger: Ledger, batch: dict[str, Any], minter: Callable[[Iterable[str]], str]
) -> NoteResult:
    """Expand one note batch into events, collecting every problem.

    Admission order: leaves, sources, closes, sweeps, checkpoints, so later
    entries may reference ids minted earlier in the batch. Events from clean
    entries are simulated against the passed ledger (which is mutated); on a
    non-empty problem list the caller discards ledger and events alike.
    """
    expansion = _Expansion(ledger, minter)
    expansion.take_keys(batch)
    expansion.take_leaves(batch.get("leaves") or [])
    expansion.take_sources(batch.get("sources") or [])
    expansion.take_closes(batch.get("closes") or [])
    expansion.take_sweeps(batch.get("sweeps") or [])
    expansion.take_checkpoints(batch.get("checkpoints") or [])
    if not expansion.staged and not expansion.result.problems:
        expansion.problem("$", "add at least one entry: the batch records nothing")
    expansion.simulate()
    return expansion.result
