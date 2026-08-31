"""Whole-session views: the resume brief, the schema card, and the pad verbs."""

from __future__ import annotations

import argparse
import difflib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from btm_corekit import (
    append_jsonl,
    emit,
    jot,
    now_iso,
    pad_body,
    pad_entries,
    recall,
    signal,
    state_root,
)
from btm_lit_review.constants import PAD_TAIL, READ_LEVELS, SOURCES, STATUSES
from btm_lit_review.draft import marker_table, refresh_markers
from btm_lit_review.notebook import (
    SCHEMA,
    finding_view,
    gap_view,
    live,
    load_notebook,
    next_id,
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


def extraction_keys(directory: Path) -> set[str]:
    return {
        entry["body"].get("key")
        for entry in pad_entries(directory)
        if entry["body"].get("kind") == "extraction"
    }


def unextracted(directory: Path, papers: Mapping[str, Paper]) -> list[str]:
    """Included papers with no extraction entry on the pad."""
    covered = extraction_keys(directory)
    return [
        key
        for key, paper in papers.items()
        if paper.status == "included" and key not in covered
    ]


def drift(records: list[dict[str, Any]], papers: Mapping[str, Paper]) -> dict[str, Any]:
    """Corpus movement since the last brief; empty on a first run."""
    current = {key: paper.status for key, paper in papers.items()}
    snapshots = [record for record in records if record["e"] == "snapshot"]
    if not snapshots:
        return {"since": None}
    last = snapshots[-1]
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
        finding_view(record, papers) for record in live(records, "finding").values()
    ]
    gaps = [gap_view(record, papers) for record in live(records, "gap").values()]
    challenged = [gap["id"] for gap in gaps if gap["state"] == "challenged"]
    at_risk = [finding["id"] for finding in findings if finding["state"] == "at-risk"]
    if at_risk:
        signal(f"at-risk findings: {', '.join(at_risk)}; re-affirm or supersede")
    if challenged:
        signal(f"challenged gaps: {', '.join(challenged)}; re-affirm or supersede")
    markers = refresh_markers(session, papers)
    document = {
        "session": session.root.name,
        "question": protocol.get("question"),
        "level": protocol.get("level"),
        "drift": drift(records, papers),
        "findings": findings,
        "gaps": gaps,
        "rules": [
            {
                "id": record["id"],
                "action": record["action"],
                "pattern": record["pattern"],
                "matched": len(record["matched"]),
            }
            for record in records
            if record["e"] == "rule"
        ],
        "markers": marker_table(markers, papers),
        "unextracted": unextracted(session.root, papers),
        "pad_tail": recall(session.root, limit=PAD_TAIL)["entries"],
        "lore": [entry["body"] for entry in pad_entries(lore_dir())],
    }
    emit(document)
    snapshot = {
        "e": "snapshot",
        "id": next_id(records, "snapshot"),
        "t": now_iso(),
        "papers": {key: paper.status for key, paper in papers.items()},
    }
    append_jsonl(session.notebook_path, [snapshot])
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


def cmd_jot(args: argparse.Namespace) -> int:
    session = None if args.lore else open_session(args.session)
    body, advisory = pad_body(args.entry, args.text)
    if advisory:
        signal(advisory)
    if session and body.get("kind") == "extraction":
        _recognize_extraction(body, session)
    emit(jot(lore_dir() if session is None else session.root, body))
    return 0


def _recognize_extraction(body: Mapping[str, Any], session: Session) -> None:
    """Advisories only: the jot stands whatever these say."""
    papers = load_papers(session)
    key = str(body.get("key") or "")
    if key not in papers:
        near = difflib.get_close_matches(key, papers, n=3, cutoff=0.5)
        hint = f"; did you mean: {', '.join(near)}" if near else ""
        signal(f"extraction key '{key}' is not a corpus paper{hint}")
    elif papers[key].read_level == "none":
        signal(f"{key} has read_level none; record the read level via update")


def cmd_recall(args: argparse.Namespace) -> int:
    emit(
        recall(
            pad_directory(args),
            kind=args.kind,
            match=args.match,
            since=args.since,
            limit=args.limit,
        )
    )
    return 0
