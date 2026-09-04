"""Whole-session views: the resume brief, the schema card, and the pad verbs."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from btm_corekit import (
    JSON,
    emit,
    now_iso,
    pad_entries,
    signal,
    state_root,
    suggest,
    write_atomic,
)
from btm_lit_review.constants import PAD_TAIL, READ_LEVELS, SOURCES, STATUSES
from btm_lit_review.draft import marker_table, refresh_markers
from btm_lit_review.notebook import (
    SCHEMA,
    FindingRecord,
    GapRecord,
    RuleRecord,
    arrivals_of,
    finding_view,
    gap_view,
    live,
    load_notebook,
)
from btm_lit_review.paper import Paper
from btm_lit_review.session import Session, load_papers, load_protocol, open_session

PAD_SCHEMA = (
    'jot stores any JSON object; {"kind": "extraction", "key": "<paper key>", ...} '
    "is recognized for coverage; map, open, and lore are suggested kinds; "
    "--lore keeps cross-session tool notes"
)


def lore_dir() -> Path:
    return state_root("lit-review") / "lore"


def extraction_keys(entries: list[dict[str, Any]]) -> set[str]:
    return {
        entry["body"].get("key")
        for entry in entries
        if entry["body"].get("kind") == "extraction"
    }


def unextracted_in(
    entries: list[dict[str, Any]], papers: Mapping[str, Paper]
) -> list[str]:
    """Included papers with no extraction entry among the pad entries."""
    covered = extraction_keys(entries)
    return [
        key
        for key, paper in papers.items()
        if paper.status == "included" and key not in covered
    ]


def unextracted(directory: Path, papers: Mapping[str, Paper]) -> list[str]:
    return unextracted_in(pad_entries(directory), papers)


def load_snapshot(session: Session) -> dict[str, Any] | None:
    """The previous brief's corpus statuses; one file, replaced per brief, so
    the notebook never grows by the corpus size on every resume."""
    path = session.snapshot_path
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def drift(last: dict[str, Any] | None, papers: Mapping[str, Paper]) -> dict[str, Any]:
    """Corpus movement since the last brief; empty on a first run."""
    current = {key: paper.status for key, paper in papers.items()}
    if last is None:
        return {"since": None}
    changed = [
        {"key": key, "from": before, "to": current[key]}
        for key, before in last["papers"].items()
        if key in current and current[key] != before
    ]
    return {
        "since": last["id"],
        "new_papers": [key for key in current if key not in last["papers"]],
        "status_changes": changed,
    }


def cmd_brief(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    papers = load_papers(session)
    records = load_notebook(session)
    findings = [
        finding_view(record, papers) for record in live(records, FindingRecord).values()
    ]
    arrivals = arrivals_of(papers)
    gaps = [gap_view(record, arrivals) for record in live(records, GapRecord).values()]
    challenged = [str(gap["id"]) for gap in gaps if gap["state"] == "challenged"]
    at_risk = [
        str(finding["id"]) for finding in findings if finding["state"] == "at-risk"
    ]
    if at_risk:
        signal(f"at-risk findings: {', '.join(at_risk)}; re-affirm or supersede")
    if challenged:
        signal(f"challenged gaps: {', '.join(challenged)}; re-affirm or supersede")
    markers = refresh_markers(session, papers)
    entries = pad_entries(session.root)
    last = load_snapshot(session)
    document: dict[str, JSON] = {
        "session": session.root.name,
        "question": protocol.question,
        "level": protocol.level,
        "drift": drift(last, papers),
        "findings": findings,
        "gaps": gaps,
        "rules": [
            {
                "id": record.id,
                "action": record.action,
                "pattern": record.pattern,
                "matched": len(record.matched),
            }
            for record in records
            if isinstance(record, RuleRecord)
        ],
        "markers": marker_table(markers, papers),
        "unextracted": unextracted_in(entries, papers),
        "pad_tail": entries[-PAD_TAIL:],
        "lore": [entry["body"] for entry in pad_entries(lore_dir())],
    }
    emit(document)
    count = (last or {}).get("n", 0) + 1
    snapshot = {
        "id": f"b{count}",
        "n": count,
        "t": now_iso(),
        "papers": {key: paper.status for key, paper in papers.items()},
    }
    write_atomic(session.snapshot_path, json.dumps(snapshot) + "\n")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    emit(
        {
            "paper": "key title year authors venue doi arxiv_id openalex_id "
            f"cited_by_count abstract pdf_url landing_url found_by status "
            f"decision_reason read_level; status in {'|'.join(STATUSES)}, "
            f"read_level in {'|'.join(READ_LEVELS)}",
            "decision": '{"<key>": {"status": "...", "reason": "...", '
            '"read_level": "..."}} on stdin to update',
            "note_batch": SCHEMA,
            "pad": PAD_SCHEMA,
            "search_log": "search: {id, command, source, query, from_year, to_year, "
            "limit, criteria_hash, time, fetched, new, total_matches, truncated}; "
            "snowball carries seed and direction in place of source and query; "
            f"sources: {', '.join(SOURCES)}",
            "verify": '{"checked": n, "broken_dois": [...], "results": [{key, '
            "title, doi_resolves, doi_http_status, crossref_title_match}]}",
            "exit_codes": "0 done (stderr signals are advisory); 1 fix the input "
            "and resend; 2 upstream failed, retry",
        }
    )
    return 0


def pad_directory(args: argparse.Namespace) -> Path:
    if args.lore:
        return lore_dir()
    return open_session(args.session).root


def recognize_extraction(args: argparse.Namespace, body: Mapping[str, Any]) -> None:
    """Advisories only: the jot stands whatever these say."""
    if args.lore or body.get("kind") != "extraction":
        return
    papers = load_papers(open_session(args.session))
    key = str(body.get("key") or "")
    if key not in papers:
        near = suggest(key, papers)
        hint = f"; did you mean: {', '.join(near)}" if near else ""
        signal(f"extraction key '{key}' is not a corpus paper{hint}")
    elif papers[key].read_level == "none":
        signal(f"{key} has read_level none; record the read level via update")
