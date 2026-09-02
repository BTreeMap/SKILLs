"""The batch gate's shared mechanics: problems accumulate, nothing raises.

A member subclasses Admission and adds its own record semantics; what lives
here is the part every gate repeats: unknown keys and fields, list shape,
reference resolution with did-you-mean, keyword minting with duplicate and
band checks, and pad-provenance links. Every check is O(entry) or
O(pool) with pools in the low hundreds.
"""

from __future__ import annotations

import difflib
import heapq
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from btm_corekit.errors import CommandError
from btm_corekit.identifiers import (
    Ambiguous,
    Exact,
    NoMatch,
    Recovered,
    band_signal,
    keywords_of,
    resolve,
    slugify,
)
from btm_corekit.verdicts import Diagnostic

Minter = Callable[[Iterable[str]], str]


def field_text(entry: Mapping[str, Any], key: str) -> str | None:
    """A non-empty string field, stripped; anything else reads as absent."""
    value = entry.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def suggest(ref: str, pool: Iterable[str], limit: int = 3) -> list[str]:
    """Closest ids to a failed reference: keyword overlap first, then edit
    distance for keys that carry no keywords (DOIs, titles)."""
    ids = list(pool)
    words = set(keywords_of(ref))
    best = heapq.nsmallest(
        limit,
        ((len(words & set(keywords_of(candidate))), candidate) for candidate in ids),
        key=lambda pair: (-pair[0], pair[1]),
    )
    near = [candidate for overlap, candidate in best if overlap > 0]
    return near or difflib.get_close_matches(ref, ids, n=limit, cutoff=0.5)


@dataclass(slots=True)
class Pool:
    """One record kind's identifier space: existing ids plus this batch's."""

    label: str
    ids: list[str]
    slugs: set[str] = field(default_factory=set)
    minted: dict[str, str] = field(default_factory=dict)  # stem -> full id
    fresh: set[str] = field(default_factory=set)  # ids minted in this batch


class Admission:
    """Accumulates corrective orders and advisories for one batch."""

    def __init__(self, mint: Minter | None = None, pad: Collection[str] = ()) -> None:
        self.mint = mint
        self.pad = set(pad)
        self.problems: list[Diagnostic] = []
        self.advisories: list[str] = []

    @property
    def clean(self) -> bool:
        return not self.problems

    def fail(self, where: str, fix: str, hint: str | None = None) -> None:
        self.problems.append(Diagnostic(where, fix, hint))

    def keys(self, batch: Mapping[str, Any], allowed: Collection[str]) -> None:
        for key in batch:
            if key not in allowed:
                self.fail(
                    key,
                    f"remove or rename the unknown key '{key}'",
                    f"valid keys: {', '.join(allowed)}",
                )

    def rows(
        self, entries: Any, key: str, schema: Mapping[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """The entries under one batch key as objects; a wrong shape is one
        problem and an empty list, so the other keys still run."""
        if entries is None:
            return []
        if not isinstance(entries, list) or not all(
            isinstance(e, dict) for e in entries
        ):
            self.fail(
                key, f"{key} is a list of objects", schema.get(key) if schema else None
            )
            return []
        return entries

    def shape(
        self, entry: Mapping[str, Any], allowed: Collection[str], where: str
    ) -> bool:
        clean = True
        for name in sorted(set(entry) - set(allowed)):
            self.fail(
                where,
                f"remove the unknown field '{name}'",
                f"gated fields: {', '.join(sorted(allowed))}; free-form notes "
                "belong on the pad (jot)",
            )
            clean = False
        return clean

    def resolve_ref(self, ref: str, pool: Pool, where: str) -> str | None:
        match resolve(ref, pool.ids):
            case Exact(full):
                return full
            case Recovered(full):
                if full not in pool.fresh:
                    self.advisories.append(
                        f"recovered {pool.label} '{ref}' -> {full}; use the full id"
                    )
                return full
            case Ambiguous(candidates):
                self.fail(
                    where,
                    f"replace '{ref}': it matches several {pool.label}s",
                    f"write one of: {', '.join(candidates)}",
                )
            case NoMatch():
                near = suggest(ref, pool.ids)
                self.fail(
                    where,
                    f"replace '{ref}': no {pool.label} matches it",
                    f"did you mean: {', '.join(near)}"
                    if near
                    else f"declare the {pool.label} earlier in this batch or fix "
                    "the spelling",
                )
        return None

    def mint_id(self, entry: Mapping[str, Any], pool: Pool, where: str) -> str | None:
        """Mint from `ref` (one explicit stem) or `kw` (two or three words)."""
        if self.mint is None:
            raise CommandError("this admission mints nothing")
        explicit = field_text(entry, "ref")
        words = [explicit] if explicit else entry.get("kw")
        if (
            not isinstance(words, list)
            or not words
            or not all(isinstance(w, str) for w in words)
        ):
            self.fail(where, 'add "kw": ["two", "words"]')
            return None
        try:
            stem = slugify(words)
        except CommandError as err:
            self.fail(where, str(err))
            return None
        if stem in pool.slugs:
            self.fail(where, f"vary one keyword: '{stem}' already minted in this batch")
            return None
        if advice := band_signal(stem):
            self.advisories.append(advice)
        full = self.mint(words)
        pool.slugs.add(stem)
        pool.ids.append(full)
        pool.minted[stem] = full
        pool.fresh.add(full)
        return full

    def links(self, entry: Mapping[str, Any], where: str) -> tuple[str, ...] | None:
        """Pad-provenance ids under `from`, each one an existing pad entry."""
        raw = entry.get("from") or []
        if not isinstance(raw, list) or not all(isinstance(p, str) for p in raw):
            self.fail(f"{where}.from", "from is a list of pad ids like j12")
            return None
        clean = True
        for index, pad_id in enumerate(raw):
            if pad_id not in self.pad:
                self.fail(
                    f"{where}.from[{index}]",
                    f"replace '{pad_id}': no pad entry has this id",
                    "recall lists pad ids",
                )
                clean = False
        return tuple(raw) if clean else None
