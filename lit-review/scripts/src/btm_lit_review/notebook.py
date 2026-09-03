"""The gated notebook: findings, gaps, rules, and snapshots derivations run on.

Free exploration belongs on the pad. A record admitted here is one the
script will later judge, so admission is total and strict: every problem
comes back in one verdict, and the file changes only when the list is
empty. Verdicts are never stored; finding_view and gap_view derive them
from live corpus state, so a claim can never go stale silently.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from btm_corekit import (
    Admission,
    Diagnostic,
    advise,
    append_jsonl,
    emit,
    keywords_of,
    now_iso,
    pad_ids,
    prefixed_number,
    read_batch,
    read_jsonl,
    rejection,
    suggest,
)
from btm_lit_review.constants import READ_RANK
from btm_lit_review.paper import (
    Paper,
    normalize_arxiv_id,
    normalize_doi,
    normalize_title,
    paper_aliases,
)
from btm_lit_review.session import Session, load_papers, open_session

NOTE_KEYS = ("findings", "gaps")
SCHEMA: dict[str, str] = {
    "findings": '{"claim": "...", "support": ["<paper key>" or {"key": "...", '
    '"needs": "abstract|full-text"}], "from": ["<pad id>"], '
    '"supersedes": "<finding id>"}',
    "gaps": '{"statement": "the absence claimed", "probes": ["<search log id>"], '
    '"watch": "word|phrase|... matched literally in title+abstract", '
    '"from": ["<pad id>"], "supersedes": "<gap id>"}',
}
FINDING_FIELDS = frozenset({"claim", "support", "from", "supersedes"})
GAP_FIELDS = frozenset({"statement", "probes", "watch", "from", "supersedes"})
ID_PREFIX = {"finding": "f", "gap": "g", "rule": "r"}
WATCH_MAX = 200  # a watch is a few words; brief scans it per paper


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


def load_notebook(session: Session) -> list[dict[str, Any]]:
    path = session.notebook_path
    return read_jsonl(path) if path.exists() else []


def next_id(records: list[dict[str, Any]], kind: str) -> str:
    count = sum(1 for record in records if record["e"] == kind)
    return f"{ID_PREFIX[kind]}{count + 1}"


def live(records: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    """Latest-wins fold of the supersede chains; ids are never reused."""
    alive: dict[str, dict[str, Any]] = {}
    for record in records:
        if record["e"] != kind:
            continue
        alive[record["id"]] = record
        alive.pop(record.get("supersedes") or "", None)
    return alive


def first_log_number(paper: Paper) -> int:
    """The search-log round that first brought the paper in; 0 when unknown."""
    for stamp in paper.found_by[:1]:
        if (number := prefixed_number(stamp, "s")) is not None:
            return number
    return 0


def finding_view(record: Mapping[str, Any], papers: Mapping[str, Paper]) -> dict:
    issues = []
    for support in record["support"]:
        paper = papers.get(support["key"])
        if paper is None:
            issues.append(f"{support['key']} left the corpus")
        elif paper.status != "included":
            issues.append(f"{support['key']} is {paper.status}")
        elif READ_RANK[paper.read_level] < READ_RANK[support["needs"]]:
            issues.append(
                f"{support['key']} read at {paper.read_level}, needs {support['needs']}"
            )
    view = {
        "id": record["id"],
        "claim": record["claim"],
        "support": record["support"],
        "state": "supported" if not issues else "at-risk",
    }
    return view | ({"issues": issues} if issues else {})


def gap_view(
    record: Mapping[str, Any], arrivals: Mapping[str, tuple[int, str]]
) -> dict:
    """A gap is challenged by papers that arrived after it and match its watch."""
    hits = []
    if record.get("watch"):
        terms = watch_terms(record["watch"])
        hits = [
            key
            for key, (arrived, folded) in arrivals.items()
            if arrived > record["seen"] and watch_hits(terms, folded)
        ]
    view = {
        "id": record["id"],
        "statement": record["statement"],
        "probes": record["probes"],
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
        existing: list[dict[str, Any]],
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
        self.counts: Counter[str] = Counter(record["e"] for record in existing)
        self.ids: defaultdict[str, set[str]] = defaultdict(set)
        for record in existing:
            self.ids[record["e"]].add(record["id"])

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

    def take_links(self, entry: Mapping[str, Any], kind: str, where: str) -> bool:
        clean = self.links(entry, where) is not None
        if target := entry.get("supersedes"):
            known = self.ids[kind]
            if target not in known:
                self.fail(
                    f"{where}.supersedes",
                    f"replace '{target}': no {kind} has this id",
                    hint=f"existing {kind} ids: {', '.join(sorted(known)) or 'none'}",
                )
                clean = False
        return clean

    def admit(
        self, kind: str, record: dict[str, Any], entry: Mapping[str, Any]
    ) -> None:
        record["e"] = kind
        self.counts[kind] += 1
        record["id"] = f"{ID_PREFIX[kind]}{self.counts[kind]}"
        self.ids[kind].add(record["id"])
        record["t"] = now_iso()
        if entry.get("from"):
            record["from"] = list(entry["from"])
        if entry.get("supersedes"):
            record["supersedes"] = entry["supersedes"]
        self.records.append(record)
        self.admitted[f"{kind}s"].append(record["id"])

    def take_findings(self, entries: Any) -> None:
        for index, entry in enumerate(self.rows(entries, "findings", SCHEMA)):
            where = f"findings[{index}]"
            clean = self.shape(entry, FINDING_FIELDS, where)
            claim = str(entry.get("claim") or "").strip()
            if not claim:
                self.fail(where, "state the claim", hint=SCHEMA["findings"])
                clean = False
            support = self._support(entry.get("support"), where)
            clean = clean and support is not None
            clean = self.take_links(entry, "finding", where) and clean
            if clean:
                self.admit("finding", {"claim": claim, "support": support}, entry)

    def _support(self, raw: Any, where: str) -> list[dict[str, str]] | None:
        if not isinstance(raw, list) or not raw:
            self.fail(
                where,
                "cite at least one supporting paper",
                hint=SCHEMA["findings"],
            )
            return None
        parsed: list[dict[str, str]] = []
        clean = True
        for j, item in enumerate(raw):
            spot = f"{where}.support[{j}]"
            token = item.get("key") if isinstance(item, dict) else item
            key = self.resolve_key(str(token or ""), spot)
            if key is None:
                clean = False
                continue
            needs = item.get("needs") if isinstance(item, dict) else None
            if needs is None:
                paper = self.papers[key]
                needs = paper.read_level if paper.read_level != "none" else "abstract"
            elif needs not in ("abstract", "full-text"):
                self.fail(
                    spot,
                    f"replace needs '{needs}'",
                    hint="needs is the honesty floor: abstract or full-text",
                )
                clean = False
                continue
            parsed.append({"key": key, "needs": needs})
        return parsed if clean else None

    def take_gaps(self, entries: Any) -> None:
        for index, entry in enumerate(self.rows(entries, "gaps", SCHEMA)):
            where = f"gaps[{index}]"
            clean = self.shape(entry, GAP_FIELDS, where)
            statement = str(entry.get("statement") or "").strip()
            if not statement:
                self.fail(where, "state the absence claimed", hint=SCHEMA["gaps"])
                clean = False
            probes = list(entry.get("probes") or [])
            for j, probe in enumerate(probes):
                number = prefixed_number(str(probe), "s")
                if number is None or not 1 <= number <= self.log_count:
                    self.fail(
                        f"{where}.probes[{j}]",
                        f"replace '{probe}': no search log entry has this id",
                        hint=f"the log holds s1..s{self.log_count}",
                    )
                    clean = False
            if not probes:
                self.advisories.append(
                    f"{where}: no probe evidence; run the null search and cite "
                    "its log id"
                )
            watch = entry.get("watch")
            if watch is not None and (
                not isinstance(watch, str)
                or len(watch) > WATCH_MAX
                or not watch_terms(watch)
            ):
                self.fail(
                    f"{where}.watch",
                    f"write the watch as words separated by |, under {WATCH_MAX} "
                    "characters",
                    hint="the words a challenger would use in its title or abstract",
                )
                clean = False
                watch = None
            clean = self.take_links(entry, "gap", where) and clean
            if clean:
                record: dict[str, Any] = {
                    "statement": statement,
                    "probes": probes,
                    "seen": self.log_count,
                }
                if watch:
                    record["watch"] = watch
                self.admit("gap", record, entry)


def expand_notes(
    batch: dict[str, Any],
    papers: Mapping[str, Paper],
    log_count: int,
    pad: set[str],
    existing: list[dict[str, Any]],
) -> NoteResult:
    """Expand one note batch into records, collecting every problem."""
    admission = _Admission(papers, log_count, pad, existing)
    admission.keys(batch, NOTE_KEYS)
    admission.take_findings(batch.get("findings"))
    admission.take_gaps(batch.get("gaps"))
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
    batch = read_batch(args.file)
    if isinstance(batch, Diagnostic):
        emit(rejection([batch], "notebook"))
        return 1
    papers = load_papers(session)
    log_count = len(read_jsonl(session.log_path))
    records = load_notebook(session)
    result = expand_notes(batch, papers, log_count, pad_ids(session.root), records)
    advise(result.advisories)
    if result.problems:
        emit(rejection(result.problems, "notebook"))
        return 1
    append_jsonl(session.notebook_path, result.records)
    everything = records + result.records
    emit(
        {
            "admitted": result.admitted,
            "findings": len(live(everything, "finding")),
            "gaps": len(live(everything, "gap")),
        }
    )
    return 0
