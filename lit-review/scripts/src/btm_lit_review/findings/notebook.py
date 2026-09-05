"""The gated notebook: findings, gaps, rules, and snapshots derivations run on.

Admission is total and strict, so one verdict names every problem in a
batch; verdicts themselves are never stored, only derived from live corpus
state.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, TypeVar

from pydantic import (
    AfterValidator,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
)

from btm_corekit import (
    JSON,
    Admission,
    Count,
    Diagnostic,
    Model,
    NonEmpty,
    append_jsonl,
    count_lines,
    dump,
    gated,
    keywords_of,
    normalize_arxiv_id,
    normalize_doi,
    now_iso,
    pad_ids,
    parse_with,
    prefixed_number,
    read_jsonl,
    salvage,
    suggest,
)
from btm_lit_review.constants import READ_RANK, ReadLevel, Status
from btm_lit_review.corpus.paper import (
    Paper,
    normalize_title,
    paper_aliases,
)
from btm_lit_review.session import Session, load_papers, open_session

SCHEMA: dict[str, str] = {
    "findings": '{"claim": "...", "support": ["<paper key>" or {"key": "...", '
    '"needs": "abstract|full-text"}], "from": ["<pad id>"], '
    '"supersedes": "<finding id>"}',
    "gaps": '{"statement": "the absence claimed", "probes": ["<search log id>"], '
    '"watch": "word|phrase|... matched literally in title+abstract", '
    '"from": ["<pad id>"], "supersedes": "<gap id>"}',
}
ID_PREFIX = {"finding": "f", "gap": "g", "rule": "r"}
WATCH_MAX = 200  # a watch is a few words; brief scans it per paper

S = TypeVar("S", bound="Superseding")


def _has_terms(watch: str) -> str:
    if not watch_terms(watch):
        raise ValueError("write the watch as words separated by |")
    return watch


Watch = Annotated[
    str, StringConstraints(max_length=WATCH_MAX), AfterValidator(_has_terms)
]


def _cited(row: Mapping[str, Any]) -> tuple[str, ...]:
    """The support keys of a row too malformed to decode; a key resolves
    against the corpus, so it stays checkable."""
    raw = row.get("support")
    if not isinstance(raw, list):
        return ()
    tokens = (item.get("key") if isinstance(item, dict) else item for item in raw)
    return tuple(token for token in tokens if isinstance(token, str))


def _as_support(raw: Any) -> Any:
    """A support entry is a key, or a key with the read level it needs."""
    return {"key": raw} if isinstance(raw, str) else raw


class SupportEntry(Model):
    key: NonEmpty
    needs: Literal[ReadLevel.ABSTRACT, ReadLevel.FULL_TEXT] | None = None


Support = Annotated[SupportEntry, BeforeValidator(_as_support)]


class Linked(Model):
    """What both note kinds carry: provenance and the record they replace."""

    from_: tuple[str, ...] = Field(default=(), alias="from")
    supersedes: str | None = None


class FindingEntry(Linked):
    claim: NonEmpty
    support: tuple[Support, ...] = Field(min_length=1)


class GapEntry(Linked):
    statement: NonEmpty
    probes: tuple[str, ...] = ()
    watch: Watch | None = None


class Recorded(Model):
    """What the notebook stamps on every record it admits."""

    id: str
    t: str = ""


class Superseding(Recorded):
    """A record a later one may replace, carrying where it came from."""

    from_: tuple[str, ...] = Field(default=(), alias="from")
    supersedes: str | None = None


class SupportRow(Model):
    key: NonEmpty
    needs: ReadLevel


class FindingRecord(Superseding):
    e: Literal["finding"]
    claim: NonEmpty
    support: tuple[SupportRow, ...] = Field(min_length=1)


class GapRecord(Superseding):
    e: Literal["gap"]
    statement: NonEmpty
    probes: tuple[str, ...] = ()
    seen: Count = 0
    watch: str | None = None


class RuleRecord(Recorded):
    e: Literal["rule"]
    on: str
    pattern: str
    action: Status
    reason: str
    matched: tuple[str, ...] = ()


NotebookRecord = FindingRecord | GapRecord | RuleRecord
RECORD: TypeAdapter[list[NotebookRecord]] = TypeAdapter(
    list[Annotated[NotebookRecord, Field(discriminator="e")]]
)


Rows = tuple[Mapping[str, Any], ...]


class NoteBatch(Model):
    """The container. Rows stay opaque here and decode one at a time, so a
    row with a bad field still lets its neighbours reach the corpus checks."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    findings: Rows = ()
    gaps: Rows = ()


NOTE_KEYS = tuple(NoteBatch.model_fields)


def watch_terms(watch: str) -> list[str]:
    """The literal terms of a watch: `|`-separated, trimmed, non-empty, and
    casefolded here so `watch_hits` can never be handed unfolded terms."""
    return [folded for term in watch.split("|") if (folded := term.strip().casefold())]


def watch_hits(terms: Sequence[str], folded: str) -> bool:
    """Substring test per term against an already-folded haystack: each `in`
    is one C-level two-way search, and neither side is folded per call."""
    return any(term in folded for term in terms)


def arrivals_of(papers: Mapping[str, Paper]) -> dict[str, tuple[int, str]]:
    """Per paper, the log round it arrived in and the folded text a watch
    reads; folded once per brief and shared by every gap view."""
    return {
        key: (
            first_log_number(paper),
            f"{paper.title} {paper.abstract or ''}".casefold(),
        )
        for key, paper in papers.items()
    }


def load_notebook(session: Session) -> list[NotebookRecord]:
    """The notebook as records; a hand-edited line is a located rejection."""
    path = session.notebook_path
    if not path.exists():
        return []
    return parse_with(RECORD, read_jsonl(path), str(path))


def next_id(records: Sequence[NotebookRecord], kind: str) -> str:
    count = sum(1 for record in records if record.e == kind)
    return f"{ID_PREFIX[kind]}{count + 1}"


def live(records: Sequence[NotebookRecord], kind: type[S]) -> dict[str, S]:
    """Latest-wins fold of the supersede chains; ids are never reused."""
    alive: dict[str, S] = {}
    for record in records:
        if not isinstance(record, kind):
            continue
        alive[record.id] = record
        alive.pop(record.supersedes or "", None)
    return alive


def first_log_number(paper: Paper) -> int:
    """The search-log round that first brought the paper in; 0 when unknown."""
    for stamp in paper.found_by[:1]:
        if (number := prefixed_number(stamp, "s")) is not None:
            return number
    return 0


def finding_view(record: FindingRecord, papers: Mapping[str, Paper]) -> dict[str, JSON]:
    issues = []
    for support in record.support:
        paper = papers.get(support.key)
        if paper is None:
            issues.append(f"{support.key} left the corpus")
        elif paper.status is not Status.INCLUDED:
            issues.append(f"{support.key} is {paper.status}")
        elif READ_RANK[paper.read_level] < READ_RANK[support.needs]:
            issues.append(
                f"{support.key} read at {paper.read_level}, needs {support.needs}"
            )
    view: dict[str, JSON] = {
        "id": record.id,
        "claim": record.claim,
        "support": [dump(row) for row in record.support],
        "state": "supported" if not issues else "at-risk",
    }
    return view | ({"issues": issues} if issues else {})


def gap_view(
    record: GapRecord, arrivals: Mapping[str, tuple[int, str]]
) -> dict[str, JSON]:
    """A gap is challenged by papers that arrived after it and match its watch."""
    hits: list[str] = []
    if record.watch:
        terms = watch_terms(record.watch)
        hits = [
            key
            for key, (arrived, folded) in arrivals.items()
            if arrived > record.seen and watch_hits(terms, folded)
        ]
    view: dict[str, JSON] = {
        "id": record.id,
        "statement": record.statement,
        "probes": list(record.probes),
        "state": "standing" if not hits else "challenged",
    }
    return view | ({"hits": hits} if hits else {})


@dataclass(slots=True)
class NoteResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    admitted: dict[str, list[str]] = field(
        default_factory=lambda: {"findings": [], "gaps": []}
    )
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)


class _Admission(Admission):
    """One batch working through validation; every method appends, none raises."""

    def __init__(
        self,
        papers: Mapping[str, Paper],
        log_count: int,
        pad: set[str],
        existing: Sequence[NotebookRecord],
    ) -> None:
        super().__init__(pad=pad)
        self.papers = papers
        self.log_count = log_count
        self.records: list[dict[str, Any]] = []
        self.admitted: dict[str, list[str]] = {"findings": [], "gaps": []}
        self.aliases = {
            alias: key
            for key, paper in papers.items()
            for alias in paper_aliases(paper)
        }
        self._key_words: dict[str, set[str]] = {}
        self.counts: Counter[str] = Counter(record.e for record in existing)
        self.ids: defaultdict[str, set[str]] = defaultdict(set)
        for record in existing:
            self.ids[record.e].add(record.id)

    def key_words(self) -> dict[str, set[str]]:
        """Keyword sets per corpus key, built on the first failed token."""
        if not self._key_words:
            self._key_words = {key: set(keywords_of(key)) for key in self.papers}
        return self._key_words

    def resolve_key(self, token: str, where: str) -> str | None:
        """A paper key, or any alias a model plausibly writes: DOI, arXiv id,
        title."""
        if token in self.papers:
            return token
        candidates = (
            token,
            f"doi:{normalize_doi(token)}",
            f"arxiv:{normalize_arxiv_id(token)}",
            f"title:{normalize_title(token)}",
        )
        for candidate in candidates:
            if key := self.aliases.get(candidate):
                self.advisories.append(f"{where}: resolved {token} -> {key}")
                return key
        near = suggest(token, self.papers, keywords=self.key_words())
        self.fail(
            where,
            f"replace '{token}': no corpus paper matches it",
            hint=f"did you mean: {', '.join(near)}"
            if near
            else "show --keys lists exact keys; search brings the paper in first",
        )
        return None

    def take_links(self, entry: Linked, kind: str, where: str) -> bool:
        clean = self.pad_links(entry.from_, where)
        if entry.supersedes:
            known = self.ids[kind]
            if entry.supersedes not in known:
                self.fail(
                    f"{where}.supersedes",
                    f"replace '{entry.supersedes}': no {kind} has this id",
                    hint=f"existing {kind} ids: {', '.join(sorted(known)) or 'none'}",
                )
                clean = False
        return clean

    def admit(self, kind: str, fields: dict[str, Any], entry: Linked) -> None:
        """Stamp the record and hold it; the batch commits or none of it does."""
        self.counts[kind] += 1
        minted = f"{ID_PREFIX[kind]}{self.counts[kind]}"
        self.ids[kind].add(minted)
        record = {
            "e": kind,
            "id": minted,
            "t": now_iso(),
            **fields,
            "from": list(entry.from_),
        }
        if entry.supersedes:
            record["supersedes"] = entry.supersedes
        self.records.append(record)
        self.admitted[f"{kind}s"].append(minted)

    def take_findings(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"findings[{index}]"
            entry = self.decode(FindingEntry, row, where, SCHEMA["findings"])
            if entry is None:
                for position, token in enumerate(_cited(row)):
                    self.resolve_key(token, f"{where}.support[{position}]")
                continue
            support = self._support(entry.support, where)
            clean = support is not None
            clean = self.take_links(entry, "finding", where) and clean
            if clean:
                self.admit("finding", {"claim": entry.claim, "support": support}, entry)

    def _support(
        self, entries: tuple[SupportEntry, ...], where: str
    ) -> list[dict[str, str]] | None:
        parsed: list[dict[str, str]] = []
        clean = True
        for index, item in enumerate(entries):
            spot = f"{where}.support[{index}]"
            key = self.resolve_key(item.key, spot)
            if key is None:
                clean = False
                continue
            needs = item.needs or self._floor(key)
            parsed.append({"key": key, "needs": needs})
        return parsed if clean else None

    def _floor(self, key: str) -> ReadLevel:
        """An uncited read level defaults to how deeply the paper was read,
        and to abstract when it has not been read at all."""
        level = self.papers[key].read_level
        return ReadLevel.ABSTRACT if level is ReadLevel.NONE else level

    def take_gaps(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"gaps[{index}]"
            entry = self.decode(GapEntry, row, where, SCHEMA["gaps"])
            if entry is None:
                self.probes(salvage(row, "probes"), where)
                continue
            clean = self.probes(entry.probes, where)
            if not entry.probes:
                self.advisories.append(
                    f"{where}: no probe evidence; run the null search and cite "
                    "its log id"
                )
            clean = self.take_links(entry, "gap", where) and clean
            if clean:
                record: dict[str, Any] = {
                    "statement": entry.statement,
                    "probes": list(entry.probes),
                    "seen": self.log_count,
                }
                if entry.watch:
                    record["watch"] = entry.watch
                self.admit("gap", record, entry)

    def probes(self, probes: Sequence[str], where: str) -> bool:
        """Every probe names a search the log actually holds."""
        clean = True
        for index, probe in enumerate(probes):
            number = prefixed_number(probe, "s")
            if number is None or not 1 <= number <= self.log_count:
                self.fail(
                    f"{where}.probes[{index}]",
                    f"replace '{probe}': no search log entry has this id",
                    hint=f"the log holds s1..s{self.log_count}",
                )
                clean = False
        return clean


def expand_notes(
    batch: dict[str, Any],
    papers: Mapping[str, Paper],
    log_count: int,
    pad: set[str],
    existing: Sequence[NotebookRecord],
) -> NoteResult:
    """Expand one note batch into records, collecting every problem."""
    admission = _Admission(papers, log_count, pad, existing)
    admission.known_keys(batch, NoteBatch)
    note = admission.decode(NoteBatch, batch)
    if note is not None:
        admission.take_findings(note.findings)
        admission.take_gaps(note.gaps)
    if not admission.records and admission.clean:
        admission.fail("$", "add at least one entry: the batch records nothing")
    return NoteResult(
        records=[] if admission.problems else admission.records,
        admitted=admission.admitted,
        advisories=admission.advisories,
        problems=admission.problems,
    )


def cmd_note(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    papers = load_papers(session)
    log_count = count_lines(session.log_path)
    records = load_notebook(session)

    def expand(batch: dict[str, Any]) -> NoteResult:
        return expand_notes(batch, papers, log_count, pad_ids(session.root), records)

    def commit(result: NoteResult) -> dict[str, JSON]:
        append_jsonl(session.notebook_path, result.records)
        everything = records + parse_with(RECORD, result.records, "notebook")
        return {
            "admitted": result.admitted,
            "findings": len(live(everything, FindingRecord)),
            "gaps": len(live(everything, GapRecord)),
        }

    return gated(args.file, "notebook", expand, commit)
