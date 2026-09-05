"""The batch gate's shared mechanics: problems accumulate, nothing raises. A
member subclasses Admission for its own record semantics, adding reference
resolution, id minting, and pad-link checks; each check is O(entry) or
O(pool), with pools in the low hundreds."""

from __future__ import annotations

import difflib
import heapq
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any

from pydantic import ValidationError, model_validator

from btm_corekit.records.models import Keyword, M, Model, Trimmed, diagnostics
from btm_corekit.report.errors import CommandError
from btm_corekit.report.verdicts import Diagnostic
from btm_corekit.store.identifiers import (
    Ambiguous,
    Exact,
    NoMatch,
    Recovered,
    band_signal,
    keywords_of,
    resolve,
    slugify,
)

Minter = Callable[[Iterable[str]], str]


class Named(Model):
    """An entry that mints its own id: two or three keywords, or one stem."""

    kw: tuple[Keyword, ...] = ()
    ref: Annotated[str, Trimmed] | None = None

    @property
    def words(self) -> tuple[str, ...]:
        return (self.ref,) if self.ref else self.kw

    @model_validator(mode="after")
    def _names_itself(self) -> Named:
        if not self.words:
            raise ValueError('add "kw": ["two", "words"]')
        return self


def salvage(row: Mapping[str, Any], key: str) -> tuple[str, ...]:
    """The strings under `key` in a row too malformed to decode as a whole. A
    field checked against something outside the row, a corpus key or a
    quote, stays checkable even when its neighbours are wrong."""
    raw = row.get(key)
    if not isinstance(raw, list):
        return ()
    return tuple(item for item in raw if isinstance(item, str))


def _at(outer: str, inner: str) -> str:
    """Nest one location inside another; `$` is the whole payload."""
    if inner == "$":
        return outer
    if outer == "$":
        return inner
    return f"{outer}.{inner}"


def suggest(
    ref: str,
    pool: Iterable[str],
    limit: int = 3,
    keywords: Mapping[str, set[str]] | None = None,
) -> list[str]:
    """Closest ids to a failed reference: keyword overlap first, then edit
    distance for keys with no keywords (DOIs, titles). `keywords` is a
    precomputed index; without one, each call is O(pool x words)."""
    ids = list(pool)
    words = set(keywords_of(ref))
    index = keywords if keywords is not None else {}
    best = heapq.nsmallest(
        limit,
        (
            (
                len(
                    words
                    & (
                        index[candidate]
                        if candidate in index
                        else set(keywords_of(candidate))
                    )
                ),
                candidate,
            )
            for candidate in ids
        ),
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
    _keywords: dict[str, set[str]] = field(default_factory=dict)

    def keywords(self) -> dict[str, set[str]]:
        """Keyword sets per id, extended for ids added since the last call;
        amortized O(1) per id across a batch."""
        for candidate in self.ids[len(self._keywords) :]:
            self._keywords[candidate] = set(keywords_of(candidate))
        return self._keywords


class Admission:
    """Accumulates corrective orders and advisories for one batch."""

    def __init__(self, mint: Minter | None = None, pad: Iterable[str] = ()) -> None:
        self.mint = mint
        self.pad = set(pad)
        self.problems: list[Diagnostic] = []
        self.advisories: list[str] = []

    @property
    def clean(self) -> bool:
        return not self.problems

    def fail(self, where: str, fix: str, hint: str | None = None) -> None:
        self.problems.append(Diagnostic(where, fix, hint))

    def decode(
        self,
        model: type[M],
        payload: Any,
        where: str = "$",
        hint: str | None = None,
    ) -> M | None:
        """A payload as its model, or every located problem recorded. Locations
        nest, and `hint` carries the entry's schema fragment for problems
        pydantic states without one."""
        try:
            return model.model_validate(payload)
        except ValidationError as err:
            for problem in diagnostics(err):
                self.fail(_at(where, problem.where), problem.fix, problem.hint or hint)
            return None

    def known_keys(self, payload: Mapping[str, Any], container: type[Model]) -> None:
        """Top-level keys the container does not declare. The container
        ignores extras so rows still decode; naming them here keeps a typo
        from failing silently."""
        allowed = set(container.model_fields)
        for key in payload:
            if key not in allowed:
                self.fail(
                    key,
                    f"remove or rename the unknown key '{key}'",
                    f"valid keys: {', '.join(sorted(allowed))}",
                )

    def resolve_ref(self, ref: str, pool: Pool, where: str) -> str | None:
        # The pool's keyword index serves both the match and the did-you-mean,
        # tokenized once per batch.
        match resolve(ref, pool.ids, pool.keywords()):
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
                near = suggest(ref, pool.ids, keywords=pool.keywords())
                self.fail(
                    where,
                    f"replace '{ref}': no {pool.label} matches it",
                    f"did you mean: {', '.join(near)}"
                    if near
                    else f"declare the {pool.label} earlier in this batch or fix "
                    "the spelling",
                )
        return None

    def mint_id(self, entry: Named, pool: Pool, where: str) -> str | None:
        """Mint from the entry's own words; a batch may not name one twice."""
        if self.mint is None:
            raise CommandError("this admission mints nothing")
        words = entry.words
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

    def pad_links(self, ids: Sequence[str], where: str) -> bool:
        """Every provenance id names an entry the pad actually holds."""
        clean = True
        for index, pad_id in enumerate(ids):
            if pad_id not in self.pad:
                self.fail(
                    f"{where}.from[{index}]",
                    f"replace '{pad_id}': no pad entry has this id",
                    "recall lists pad ids",
                )
                clean = False
        return clean
