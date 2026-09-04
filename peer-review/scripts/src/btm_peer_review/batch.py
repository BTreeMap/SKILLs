"""The note pipeline: parse, resolve, simulate; a rejection lists every fix.

Every phase runs to completion so one verdict carries every problem; the
ledger changes only when the problem list is empty.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any

from pydantic import AfterValidator, ConfigDict, Field

from btm_corekit import (
    Admission,
    Diagnostic,
    Model,
    Named,
    NonEmpty,
    Pool,
    salvage,
)
from btm_peer_review.constants import BANKS, CLAIM_WORDS_MAX, Bank, Kind, Severity
from btm_peer_review.ledger import apply
from btm_peer_review.state import Evidenced, Ledger
from btm_peer_review.store import Corpus
from btm_peer_review.text import Fuzzy, PaperText, Unresolved, Verbatim

SCHEMA: dict[str, str] = {
    "claims": '{"kw": ["two", "words"], "verbatim": "the claim as the paper '
    'states it, one sentence"}',
    "objections": '{"kw": ["two", "words"], "kind": "<a kind from banks>", '
    '"severity": "fatal|major|minor|question", "text": "the objection, with '
    'what would resolve it", "claim": "<claim ref> (optional)", "where": '
    '"section or table (optional)", "anchors": ["verbatim quote from the '
    'paper"], "missing": "what the paper omits (replaces anchors)", '
    '"prior": ["<corpus key>"] (required for novelty kinds), '
    '"from": ["<pad id>"] (optional provenance)}',
    "walks": '{"bank": "claims|design|analysis|limitations|novelty", '
    '"note": "what the walk found or ruled out"}',
    "withdraws": '{"objection": "<objection ref>", "reason": "why it no longer holds"}',
}


def _one_sentence(text: str) -> str:
    if len(text.split()) > CLAIM_WORDS_MAX:
        raise ValueError(f"shorten to {CLAIM_WORDS_MAX} words or fewer")
    return text


class ClaimEntry(Named):
    verbatim: Annotated[NonEmpty, AfterValidator(_one_sentence)]


class ObjectionEntry(Named, Evidenced):
    kind: Kind
    severity: Severity
    text: NonEmpty
    claim: str | None = None
    where: str | None = None
    prior: tuple[NonEmpty, ...] = ()
    from_: tuple[str, ...] = Field(default=(), alias="from")


class WalkEntry(Model):
    bank: Bank
    note: str = ""


class WithdrawEntry(Model):
    objection: NonEmpty
    reason: NonEmpty


Rows = tuple[Mapping[str, Any], ...]


class NoteBatch(Model):
    """The container. Rows stay opaque here and decode one at a time, so a
    row with a bad field still lets its neighbours reach the checks that need
    the paper and the corpus. Extras are ignored here and named by
    `known_keys`, so one unknown key cannot swallow the whole batch."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    claims: Rows = ()
    objections: Rows = ()
    walks: Rows = ()
    withdraws: Rows = ()


BATCH_KEYS = tuple(NoteBatch.model_fields)


@dataclass(frozen=True, slots=True)
class Context:
    """What admission checks quotes and prior work against."""

    paper: PaperText | None
    corpus: Corpus | None
    year: int


@dataclass(slots=True)
class NoteResult:
    events: list[dict[str, Any]] = field(default_factory=list)
    minted: dict[str, dict[str, str]] = field(default_factory=dict)
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)


class _Admission(Admission):
    """One batch's resolution context; every phase runs, problems accumulate."""

    def __init__(
        self,
        ledger: Ledger,
        context: Context,
        mint: Callable[[Iterable[str]], str],
        pad: Iterable[str],
    ) -> None:
        super().__init__(mint, pad)
        self.context = context
        self.events: list[dict[str, Any]] = []
        self.claims = Pool("claim", list(ledger.claim_order))
        self.objections = Pool("objection", list(ledger.objection_order))

    def anchor(self, quote: str, where: str) -> Verbatim | Fuzzy | None:
        if self.context.paper is None:
            self.fail(where, "ingest the paper text before quoting it")
            return None
        match self.context.paper.resolve(quote):
            case Verbatim() | Fuzzy() as hit:
                return hit
            case Unresolved(best, similarity):
                hint = (
                    f"closest page {best} at similarity {similarity}"
                    if best is not None
                    else "no span of the paper resembles it"
                )
                self.fail(
                    where, "quote the paper verbatim; this text is not in it", hint
                )
        return None

    def take_claims(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"claims[{index}]"
            entry = self.decode(ClaimEntry, row, where, SCHEMA["claims"])
            if entry is None:
                continue
            hit = self.anchor(entry.verbatim, f"{where}.verbatim")
            full = self.mint_id(entry, self.claims, where)
            if hit is None or full is None:
                continue
            self.events.append(
                {
                    "e": "claim",
                    "id": full,
                    "verbatim": entry.verbatim,
                    "page": hit.page,
                }
            )

    def take_objections(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"objections[{index}]"
            entry = self.decode(ObjectionEntry, row, where, SCHEMA["objections"])
            if entry is None:
                self.quotes(salvage(row, "anchors"), where)
                continue
            ok = self.pad_links(entry.from_, where)
            ok = self.quotes(entry.anchors, where) and ok
            claim = None
            if entry.claim is not None:
                claim = self.resolve_ref(entry.claim, self.claims, f"{where}.claim")
                ok = ok and claim is not None
            if entry.kind.bank is Bank.NOVELTY:
                ok = self.take_prior(entry.prior, where) and ok
            elif entry.prior:
                self.fail(
                    f"{where}.prior",
                    "prior keys belong to novelty kinds; drop them here",
                    f"novelty kinds: {' '.join(BANKS[Bank.NOVELTY])}",
                )
                ok = False
            full = self.mint_id(entry, self.objections, where)
            if not ok or full is None:
                continue
            self.events.append(
                {
                    "e": "objection",
                    "id": full,
                    "kind": entry.kind,
                    "severity": entry.severity,
                    "text": entry.text,
                    "claim": claim,
                    "where": entry.where,
                    "anchors": list(entry.anchors),
                    "missing": entry.missing,
                    "prior": list(entry.prior),
                    "from": list(entry.from_),
                }
            )

    def quotes(self, anchors: Sequence[str], where: str) -> bool:
        """Every anchor resolves against the paper as ingested."""
        hits = [
            self.anchor(quote, f"{where}.anchors[{index}]")
            for index, quote in enumerate(anchors)
        ]
        return all(hit is not None for hit in hits)

    def take_prior(self, prior: Sequence[str], where: str) -> bool:
        if not prior:
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
            record = corpus.lookup(key)
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
                self.advisories.append(
                    f"{spot}: '{key}' shares the paper's year; confirm it was "
                    "public first"
                )
        return ok

    def take_walks(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            entry = self.decode(WalkEntry, row, f"walks[{index}]", SCHEMA["walks"])
            if entry is not None:
                self.events.append(
                    {"e": "walk", "bank": entry.bank, "note": entry.note}
                )

    def take_withdraws(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"withdraws[{index}]"
            entry = self.decode(WithdrawEntry, row, where, SCHEMA["withdraws"])
            if entry is None:
                continue
            full = self.resolve_ref(
                entry.objection, self.objections, f"{where}.objection"
            )
            if full is not None:
                self.events.append(
                    {"e": "withdraw", "objection": full, "reason": entry.reason}
                )


def expand_batch(
    ledger: Ledger,
    batch: dict[str, Any],
    context: Context,
    mint: Callable[[Iterable[str]], str],
    pad: Iterable[str] = (),
) -> NoteResult:
    admission = _Admission(ledger, context, mint, pad)
    admission.known_keys(batch, NoteBatch)
    note = admission.decode(NoteBatch, batch)
    if note is not None:
        admission.take_claims(note.claims)
        admission.take_objections(note.objections)
        admission.take_walks(note.walks)
        admission.take_withdraws(note.withdraws)
    if admission.clean and not admission.events:
        admission.fail("$", "add at least one entry: the batch records nothing")
    result = NoteResult(
        events=[] if admission.problems else admission.events,
        minted={
            "claims": admission.claims.minted,
            "objections": admission.objections.minted,
        },
        advisories=admission.advisories,
        problems=admission.problems,
    )
    for event in result.events:
        apply(ledger, event)
    return result
