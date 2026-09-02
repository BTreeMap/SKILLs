"""The note pipeline: parse, resolve, simulate; a rejection lists every fix.

Every phase runs to completion so one verdict carries every problem; the
ledger changes only when the problem list is empty.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, TypeVar

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
from btm_peer_review.constants import (
    BANKS,
    CLAIM_WORDS_MAX,
    Bank,
    Kind,
    Severity,
)
from btm_peer_review.ledger import apply
from btm_peer_review.state import Ledger
from btm_peer_review.store import Corpus
from btm_peer_review.text import Fuzzy, PaperText, Unresolved, Verbatim, tokens

E = TypeVar("E")

BATCH_KEYS = ("claims", "objections", "walks", "withdraws")
SCHEMA: dict[str, str] = {
    "claims": '{"kw": ["two", "words"], "verbatim": "the claim as the paper '
    'states it, one sentence"}',
    "objections": '{"kw": ["two", "words"], "kind": "<a kind from banks>", '
    '"severity": "fatal|major|minor|question", "text": "the objection, with '
    'what would resolve it", "claim": "<claim ref> (optional)", "where": '
    '"section or table (optional)", "anchors": ["verbatim quote from the '
    'paper"], "missing": "what the paper omits (replaces anchors)", '
    '"prior": ["<corpus key>"] (required for novelty kinds)}',
    "walks": '{"bank": "claims|design|analysis|limitations|novelty", '
    '"note": "what the walk found or ruled out"}',
    "withdraws": '{"objection": "<objection ref>", "reason": "why it no longer holds"}',
}
KIND_HINT = ", ".join(f"{bank}: {' '.join(kinds)}" for bank, kinds in BANKS.items())
SEVERITY_HINT = ", ".join(Severity)
BANK_HINT = ", ".join(Bank)


@dataclass(frozen=True, slots=True)
class Context:
    """What admission checks quotes and prior work against."""

    paper: PaperText | None
    corpus: Corpus | None
    year: int


@dataclass(slots=True)
class Pool:
    """One record kind's identifier space: existing ids plus this batch's."""

    label: str
    ids: list[str]
    slugs: set[str] = field(default_factory=set)
    minted: dict[str, str] = field(default_factory=dict)  # stem -> full id


@dataclass(slots=True)
class NoteResult:
    events: list[dict[str, Any]] = field(default_factory=list)
    minted: dict[str, dict[str, str]] = field(default_factory=dict)
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)


def near_misses(ref: str, ids: Iterable[str]) -> list[str]:
    words = set(keywords_of(ref))
    best = heapq.nsmallest(
        3,
        ((len(words & set(keywords_of(candidate))), candidate) for candidate in ids),
        key=lambda pair: (-pair[0], pair[1]),
    )
    return [candidate for overlap, candidate in best if overlap > 0]


def _text(entry: dict[str, Any], key: str) -> str | None:
    value = entry.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


class _Admission:
    """One batch's resolution context; every phase runs, problems accumulate."""

    def __init__(
        self, ledger: Ledger, context: Context, mint: Callable[[Iterable[str]], str]
    ) -> None:
        self.context = context
        self.mint = mint
        self.result = NoteResult()
        self.claims = Pool("claim", list(ledger.claim_order))
        self.objections = Pool("objection", list(ledger.objection_order))

    def fail(self, where: str, fix: str, hint: str | None = None) -> None:
        self.result.problems.append(Diagnostic(where, fix, hint))

    def resolve_ref(self, ref: str, pool: Pool, where: str) -> str | None:
        match resolve(ref, pool.ids):
            case Exact(full) | Recovered(full):
                return full
            case Ambiguous(candidates):
                self.fail(
                    where,
                    f"'{ref}' matches several {pool.label}s; use one full id",
                    ", ".join(candidates),
                )
            case NoMatch():
                near = near_misses(ref, pool.ids)
                self.fail(
                    where,
                    f"no {pool.label} matches '{ref}'",
                    f"did you mean {', '.join(near)}" if near else None,
                )
        return None

    def mint_id(self, entry: dict[str, Any], pool: Pool, where: str) -> str | None:
        kw = entry.get("kw")
        if (
            not isinstance(kw, list)
            or not kw
            or not all(isinstance(w, str) for w in kw)
        ):
            self.fail(where, 'add "kw": ["two", "words"]')
            return None
        try:
            stem = slugify(kw)
        except CommandError as err:
            self.fail(where, str(err))
            return None
        if stem in pool.slugs:
            self.fail(where, f"kw '{stem}' repeats within the batch; vary the words")
            return None
        if advice := band_signal(stem):
            self.result.advisories.append(advice)
        pool.slugs.add(stem)
        full = self.mint(kw)
        pool.ids.append(full)
        pool.minted[stem] = full
        return full

    def anchor(self, quote: str, where: str) -> Verbatim | Fuzzy | None:
        if self.context.paper is None:
            self.fail(where, "ingest the paper text before quoting it")
            return None
        match self.context.paper.resolve(quote):
            case Verbatim() | Fuzzy() as hit:
                return hit
            case Unresolved(best, coverage):
                hint = (
                    f"closest page {best} at coverage {coverage}"
                    if best is not None
                    else "no page shares four consecutive words with it"
                )
                self.fail(
                    where, "quote the paper verbatim; this text is not in it", hint
                )
        return None

    def take_claims(self, entries: Any) -> None:
        for index, entry in enumerate(_rows(entries, "claims", self)):
            where = f"claims[{index}]"
            verbatim = _text(entry, "verbatim")
            if verbatim is None:
                self.fail(where, 'add "verbatim": the claim sentence as printed')
                continue
            if len(tokens(verbatim.lower())) > CLAIM_WORDS_MAX:
                self.fail(
                    where, f"shorten verbatim to {CLAIM_WORDS_MAX} words or fewer"
                )
                continue
            hit = self.anchor(verbatim, f"{where}.verbatim")
            full = self.mint_id(entry, self.claims, where)
            if hit is None or full is None:
                continue
            self.result.events.append(
                {"e": "claim", "id": full, "verbatim": verbatim, "page": hit.page}
            )

    def take_objections(self, entries: Any) -> None:
        for index, entry in enumerate(_rows(entries, "objections", self)):
            where = f"objections[{index}]"
            ok = True
            kind = self.vocabulary(Kind, entry, "kind", f"{where}.kind", KIND_HINT)
            severity = self.vocabulary(
                Severity, entry, "severity", f"{where}.severity", SEVERITY_HINT
            )
            text = _text(entry, "text")
            if text is None:
                self.fail(f"{where}.text", "state the objection and what resolves it")
            claim = None
            if (ref := _text(entry, "claim")) is not None:
                claim = self.resolve_ref(ref, self.claims, f"{where}.claim")
                ok = ok and claim is not None
            anchors = self.quotes(entry, where)
            missing = _text(entry, "missing")
            if anchors is None:
                ok = False
            elif not anchors and missing is None:
                self.fail(
                    where, 'add "anchors": [quotes] or "missing": what the paper omits'
                )
                ok = False
            prior = entry.get("prior") or []
            if kind is not None and kind.bank is Bank.NOVELTY:
                ok = self.take_prior(prior, where) and ok
            elif prior:
                self.fail(
                    f"{where}.prior",
                    "prior keys belong to novelty kinds; drop them here",
                    f"novelty kinds: {' '.join(BANKS[Bank.NOVELTY])}",
                )
                ok = False
            full = self.mint_id(entry, self.objections, where)
            if not ok or None in (full, kind, severity, text):
                continue
            self.result.events.append(
                {
                    "e": "objection",
                    "id": full,
                    "kind": kind,
                    "severity": severity,
                    "text": text,
                    "claim": claim,
                    "where": _text(entry, "where"),
                    "anchors": anchors,
                    "missing": missing if not anchors else None,
                    "prior": [str(p).strip() for p in prior],
                }
            )

    def vocabulary(
        self,
        cls: Callable[[Any], E],
        entry: dict[str, Any],
        key: str,
        where: str,
        hint: str,
    ) -> E | None:
        try:
            return cls(_text(entry, key))
        except ValueError:
            self.fail(where, f"use one of the {key} vocabulary", hint)
            return None

    def quotes(self, entry: dict[str, Any], where: str) -> list[str] | None:
        """Anchors as stripped strings, each resolved; None when malformed."""
        anchors = entry.get("anchors") or []
        if not isinstance(anchors, list) or not all(
            isinstance(a, str) for a in anchors
        ):
            self.fail(f"{where}.anchors", "anchors is a list of verbatim quotes")
            return None
        stripped = [a.strip() for a in anchors]
        hits = [
            self.anchor(quote, f"{where}.anchors[{a_index}]")
            for a_index, quote in enumerate(stripped)
        ]
        return stripped if all(hit is not None for hit in hits) else None

    def take_prior(self, prior: Any, where: str) -> bool:
        if not isinstance(prior, list) or not prior:
            self.fail(
                f"{where}.prior",
                "a novelty objection names the prior work as corpus keys",
                "search it with lit-review, then cite its key",
            )
            return False
        corpus = self.context.corpus
        if corpus is None:
            self.fail(
                f"{where}.prior",
                "link a lit-review corpus before objecting on novelty",
                "link <session> --corpus <lit-review session>",
            )
            return False
        ok = True
        year = self.context.year
        for p_index, key in enumerate(prior):
            record = corpus.lookup(str(key))
            spot = f"{where}.prior[{p_index}]"
            if record is None:
                self.fail(spot, f"'{key}' is not in the linked corpus")
                ok = False
            elif record.year is None:
                self.fail(spot, f"'{key}' has no year; an undated work cannot predate")
                ok = False
            elif record.year > year:
                self.fail(spot, f"'{key}' ({record.year}) postdates the paper ({year})")
                ok = False
            elif record.year == year:
                self.result.advisories.append(
                    f"{spot}: '{key}' shares the paper's year; confirm it was "
                    "public first"
                )
        return ok

    def take_walks(self, entries: Any) -> None:
        for index, entry in enumerate(_rows(entries, "walks", self)):
            bank = self.vocabulary(
                Bank, entry, "bank", f"walks[{index}].bank", BANK_HINT
            )
            if bank is None:
                continue
            self.result.events.append(
                {"e": "walk", "bank": bank, "note": _text(entry, "note") or ""}
            )

    def take_withdraws(self, entries: Any) -> None:
        for index, entry in enumerate(_rows(entries, "withdraws", self)):
            where = f"withdraws[{index}]"
            ref = _text(entry, "objection")
            reason = _text(entry, "reason")
            if ref is None or reason is None:
                self.fail(where, 'add "objection": <ref> and "reason": why it fails')
                continue
            full = self.resolve_ref(ref, self.objections, f"{where}.objection")
            if full is None:
                continue
            self.result.events.append(
                {"e": "withdraw", "objection": full, "reason": reason}
            )


def _rows(entries: Any, key: str, admission: _Admission) -> list[dict[str, Any]]:
    if entries is None:
        return []
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        admission.fail(key, f"{key} is a list of objects", SCHEMA[key])
        return []
    return entries


def expand_batch(
    ledger: Ledger,
    batch: dict[str, Any],
    context: Context,
    mint: Callable[[Iterable[str]], str],
) -> NoteResult:
    admission = _Admission(ledger, context, mint)
    for key in batch:
        if key not in BATCH_KEYS:
            admission.fail(
                key, f"unknown key; the batch keys are {', '.join(BATCH_KEYS)}"
            )
    admission.take_claims(batch.get("claims"))
    admission.take_objections(batch.get("objections"))
    admission.take_walks(batch.get("walks"))
    admission.take_withdraws(batch.get("withdraws"))
    result = admission.result
    result.minted = {
        "claims": admission.claims.minted,
        "objections": admission.objections.minted,
    }
    if not result.problems and not result.events:
        admission.fail("$", "the batch admits nothing; add at least one entry")
    if result.problems:
        result.events.clear()
        return result
    for event in result.events:
        apply(ledger, event)
    return result
