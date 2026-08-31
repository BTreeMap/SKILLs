"""The gated notebook: findings, gaps, rules, and snapshots derivations run on.

Free exploration belongs on the pad. A record admitted here is one the
script will later judge, so admission is total and strict: every problem
comes back in one verdict, and the file changes only when the list is
empty. Verdicts are never stored; finding_view and gap_view derive them
from live corpus state, so a claim can never go stale silently.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    Diagnostic,
    append_jsonl,
    emit,
    now_iso,
    pad_ids,
    read_jsonl,
    signal,
)
from btm_lit_review.constants import READ_LEVELS
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
    '"watch": "<regex over title+abstract>", "from": ["<pad id>"], '
    '"supersedes": "<gap id>"}',
}
FINDING_FIELDS = frozenset({"claim", "support", "from", "supersedes"})
GAP_FIELDS = frozenset({"statement", "probes", "watch", "from", "supersedes"})
ID_PREFIX = {"finding": "f", "gap": "g", "rule": "r", "snapshot": "b"}
LEVEL_RANK = {level: rank for rank, level in enumerate(READ_LEVELS)}
LOG_ID = re.compile(r"s(\d+)")


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
        if found := LOG_ID.fullmatch(stamp):
            return int(found.group(1))
    return 0


def finding_view(record: Mapping[str, Any], papers: Mapping[str, Paper]) -> dict:
    issues = []
    for support in record["support"]:
        paper = papers.get(support["key"])
        if paper is None:
            issues.append(f"{support['key']} left the corpus")
        elif paper.status != "included":
            issues.append(f"{support['key']} is {paper.status}")
        elif LEVEL_RANK[paper.read_level] < LEVEL_RANK[support["needs"]]:
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


def gap_view(record: Mapping[str, Any], papers: Mapping[str, Paper]) -> dict:
    """A gap is challenged by papers that arrived after it and match its watch."""
    hits = []
    if record.get("watch"):
        pattern = re.compile(record["watch"], re.IGNORECASE)
        hits = [
            key
            for key, paper in papers.items()
            if first_log_number(paper) > record["seen"]
            and pattern.search(f"{paper.title} {paper.abstract or ''}")
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


@dataclass(slots=True)
class _Admission:
    """One batch working through validation; every method appends, none raises."""

    papers: Mapping[str, Paper]
    log_count: int
    pad: set[str]
    existing: list[dict[str, Any]]
    result: NoteResult = field(default_factory=NoteResult)
    aliases: dict[str, str] = field(init=False)
    counts: Counter[str] = field(init=False)

    def __post_init__(self) -> None:
        self.aliases = {
            alias: key
            for key, paper in self.papers.items()
            for alias in paper_aliases(paper)
        }
        self.counts = Counter(record["e"] for record in self.existing)

    def problem(self, where: str, fix: str, hint: str | None = None) -> None:
        self.result.problems.append(Diagnostic(where, fix, hint))

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
                self.result.advisories.append(f"{where}: resolved {token} -> {key}")
                return key
        near = difflib.get_close_matches(token, self.papers, n=3, cutoff=0.5)
        self.problem(
            where,
            f"replace '{token}': no corpus paper matches it",
            hint=f"did you mean: {', '.join(near)}"
            if near
            else "show --keys lists exact keys; search brings the paper in first",
        )
        return None

    def take_shape(self, entry: Any, allowed: frozenset[str], where: str) -> bool:
        if not isinstance(entry, dict):
            self.problem(where, "make this entry a JSON object")
            return False
        clean = True
        for name in sorted(set(entry) - allowed):
            self.problem(
                where,
                f"remove the unknown field '{name}'",
                hint=f"gated fields: {', '.join(sorted(allowed))}; "
                "free-form notes belong on the pad (jot)",
            )
            clean = False
        return clean

    def take_links(self, entry: Mapping[str, Any], kind: str, where: str) -> bool:
        clean = True
        for j, pad_id in enumerate(entry.get("from") or []):
            if pad_id not in self.pad:
                self.problem(
                    f"{where}.from[{j}]",
                    f"replace '{pad_id}': no pad entry has this id",
                    hint="recall lists pad ids",
                )
                clean = False
        if target := entry.get("supersedes"):
            known = {r["id"] for r in self.existing if r["e"] == kind}
            known.update(r["id"] for r in self.result.records if r["e"] == kind)
            if target not in known:
                self.problem(
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
        record["t"] = now_iso()
        if entry.get("from"):
            record["from"] = list(entry["from"])
        if entry.get("supersedes"):
            record["supersedes"] = entry["supersedes"]
        self.result.records.append(record)
        self.result.admitted[f"{kind}s"].append(record["id"])

    def take_findings(self, entries: list[Any]) -> None:
        for index, entry in enumerate(entries):
            where = f"findings[{index}]"
            clean = self.take_shape(entry, FINDING_FIELDS, where)
            if not isinstance(entry, dict):
                continue
            claim = str(entry.get("claim") or "").strip()
            if not claim:
                self.problem(where, "state the claim", hint=SCHEMA["findings"])
                clean = False
            support = self._support(entry.get("support"), where)
            clean = clean and support is not None
            clean = self.take_links(entry, "finding", where) and clean
            if clean:
                self.admit("finding", {"claim": claim, "support": support}, entry)

    def _support(self, raw: Any, where: str) -> list[dict[str, str]] | None:
        if not isinstance(raw, list) or not raw:
            self.problem(
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
                self.problem(
                    spot,
                    f"replace needs '{needs}'",
                    hint="needs is the honesty floor: abstract or full-text",
                )
                clean = False
                continue
            parsed.append({"key": key, "needs": needs})
        return parsed if clean else None

    def take_gaps(self, entries: list[Any]) -> None:
        for index, entry in enumerate(entries):
            where = f"gaps[{index}]"
            clean = self.take_shape(entry, GAP_FIELDS, where)
            if not isinstance(entry, dict):
                continue
            statement = str(entry.get("statement") or "").strip()
            if not statement:
                self.problem(where, "state the absence claimed", hint=SCHEMA["gaps"])
                clean = False
            probes = list(entry.get("probes") or [])
            for j, probe in enumerate(probes):
                found = LOG_ID.fullmatch(str(probe))
                if not found or not 1 <= int(found.group(1)) <= self.log_count:
                    self.problem(
                        f"{where}.probes[{j}]",
                        f"replace '{probe}': no search log entry has this id",
                        hint=f"the log holds s1..s{self.log_count}",
                    )
                    clean = False
            if not probes:
                self.result.advisories.append(
                    f"{where}: no probe evidence; run the null search and cite "
                    "its log id"
                )
            watch = entry.get("watch")
            if watch is not None:
                try:
                    re.compile(watch)
                except re.error as err:
                    self.problem(
                        f"{where}.watch", f"fix the regex: {err}", hint=SCHEMA["gaps"]
                    )
                    clean = False
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
    for key in batch:
        if key not in NOTE_KEYS:
            admission.problem(
                key,
                f"remove or rename the unknown key '{key}'",
                hint=f"valid keys: {', '.join(NOTE_KEYS)}",
            )
    admission.take_findings(batch.get("findings") or [])
    admission.take_gaps(batch.get("gaps") or [])
    if not admission.result.records and not admission.result.problems:
        admission.problem("$", "add at least one entry: the batch records nothing")
    return admission.result


def cmd_note(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    if not raw.strip():
        raise CommandError("note reads the JSON batch from stdin or --file")
    try:
        batch = json.loads(raw)
    except json.JSONDecodeError as err:
        emit(
            {
                "rejected": [
                    {"where": "$", "fix": f"make the batch valid JSON: {err}"}
                ],
                "notebook": "unchanged",
            }
        )
        return 1
    if not isinstance(batch, dict):
        raise CommandError("note takes one JSON object")
    papers = load_papers(session)
    log_count = len(read_jsonl(session.log_path))
    records = load_notebook(session)
    result = expand_notes(batch, papers, log_count, pad_ids(session.root), records)
    for line in result.advisories:
        signal(line)
    if result.problems:
        emit(
            {
                "rejected": [problem.view() for problem in result.problems],
                "notebook": "unchanged",
                "next": "apply every fix above to the batch, then resend; "
                "--file makes the retry one edit",
            }
        )
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
