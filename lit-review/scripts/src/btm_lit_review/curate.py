"""Screening and reporting: decisions in, corpus views out."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from btm_corekit import CommandError, emit, read_jsonl, signal
from btm_lit_review.constants import (
    ABSTRACT_SHOW_LIMIT,
    AUTHOR_SHOW_LIMIT,
    DECISION_FIELDS,
    READ_LEVELS,
    STATUSES,
)
from btm_lit_review.paper import Paper, clean_text
from btm_lit_review.session import (
    criteria_hash,
    load_papers,
    load_protocol,
    open_session,
    save_papers,
)


def validate_decision(
    key: str, decision: Mapping[str, Any], papers: Mapping[str, Paper]
) -> None:
    if key not in papers:
        raise CommandError(f"decision names unknown paper key {key!r}")
    unknown = set(decision) - DECISION_FIELDS
    if unknown:
        raise CommandError(f"decision for {key} has unknown fields {sorted(unknown)}")
    status = decision.get("status")
    if status is not None and status not in STATUSES:
        raise CommandError(f"decision for {key} has invalid status {status!r}")
    if status == "excluded" and not clean_text(decision.get("reason")):
        raise CommandError(f"exclusion of {key} needs a non-empty reason")
    read_level = decision.get("read_level")
    if read_level is not None and read_level not in READ_LEVELS:
        raise CommandError(f"decision for {key} has invalid read_level {read_level!r}")


def cmd_update(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    raw = sys.stdin.read()
    if not raw.strip():
        raise CommandError("update reads the decisions JSON from stdin")
    try:
        decisions = json.loads(raw)
    except json.JSONDecodeError as err:
        raise CommandError(f"unreadable decisions JSON on stdin: {err}") from err
    if not isinstance(decisions, dict):
        raise CommandError("decisions must map paper keys to decision objects")
    papers = load_papers(session)
    for key, decision in decisions.items():
        validate_decision(key, decision, papers)
    changed = Counter()
    for key, decision in decisions.items():
        updates: dict[str, Any] = {}
        if "status" in decision:
            updates["status"] = decision["status"]
            changed[decision["status"]] += 1
        if "reason" in decision:
            updates["decision_reason"] = clean_text(decision["reason"])
        if "read_level" in decision:
            updates["read_level"] = decision["read_level"]
            changed[f"read:{decision['read_level']}"] += 1
        papers[key] = replace(papers[key], **updates)
    save_papers(session, papers)
    emit({"applied": len(decisions), "changes": dict(changed)})
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    matching = [
        paper for paper in load_papers(session).values() if paper.status == args.status
    ]
    matching.sort(key=lambda paper: -(paper.cited_by_count or 0))
    shown = []
    for paper in matching[: args.limit]:
        abstract = paper.abstract
        if abstract and len(abstract) > ABSTRACT_SHOW_LIMIT:
            abstract = abstract[:ABSTRACT_SHOW_LIMIT] + " [truncated]"
        shown.append(
            {
                "key": paper.key,
                "title": paper.title,
                "year": paper.year,
                "authors": list(paper.authors[:AUTHOR_SHOW_LIMIT]),
                "author_count": len(paper.authors),
                "venue": paper.venue,
                "citations": paper.cited_by_count,
                "read_level": paper.read_level,
                "abstract": abstract,
            }
        )
    if len(matching) > args.limit:
        signal(f"{len(matching) - args.limit} more {args.status} papers not shown")
    emit({"status": args.status, "total": len(matching), "papers": shown})
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    papers = load_papers(session)
    log = read_jsonl(session.log_path)
    by_status = Counter(paper.status for paper in papers.values())
    by_read = Counter(
        paper.read_level for paper in papers.values() if paper.status == "included"
    )
    current_hash = criteria_hash(protocol)
    logged_hashes = {entry.get("criteria_hash") for entry in log}
    if logged_hashes and logged_hashes != {current_hash}:
        signal(
            "criteria changed after searches ran; record the change in "
            "protocol.json amendments"
        )
    criteria = protocol.get("criteria") or {}
    emit(
        {
            "question": protocol.get("question"),
            "level": protocol.get("level"),
            "criteria_ready": bool(criteria.get("include"))
            and bool(criteria.get("exclude")),
            "criteria_hash": current_hash,
            "searches": len(log),
            "papers": dict(by_status),
            "included_read_levels": dict(by_read),
            "undecided": by_status.get("candidate", 0),
        }
    )
    return 0
