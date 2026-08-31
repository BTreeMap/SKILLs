"""Screening and reporting: decisions in, corpus views out."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from btm_corekit import CommandError, append_jsonl, emit, now_iso, read_jsonl, signal
from btm_lit_review.constants import (
    ABSTRACT_SHOW_LIMIT,
    AUTHOR_SHOW_LIMIT,
    DECISION_FIELDS,
    READ_LEVELS,
    STATUSES,
)
from btm_lit_review.notebook import load_notebook, next_id
from btm_lit_review.paper import PAPER_FIELDS, Paper, clean_text
from btm_lit_review.session import (
    criteria_hash,
    load_papers,
    load_protocol,
    open_session,
    require_criteria,
    save_papers,
)
from btm_lit_review.views import unextracted


def field_text(paper: Paper, on: str) -> str:
    return str(getattr(paper, on) or "")


def compile_match(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as err:
        raise CommandError(f"unreadable --match pattern: {err}") from err


def cmd_screen(args: argparse.Namespace) -> int:
    """One rule screens many candidates; the record keeps the count honest."""
    session = open_session(args.session)
    require_criteria(load_protocol(session))
    pattern = compile_match(args.match)
    reason = clean_text(args.reason)
    if not reason:
        raise CommandError("screen requires a non-empty --reason")
    action = "excluded" if args.exclude else "included"
    papers = load_papers(session)
    matched = [
        key
        for key, paper in papers.items()
        if paper.status == "candidate" and pattern.search(field_text(paper, args.on))
    ]
    rule_id = next_id(load_notebook(session), "rule")
    # The rule lands first: a failure between the writes leaves an inert
    # record, never a decision_reason pointing at a rule that does not exist.
    append_jsonl(
        session.notebook_path,
        [
            {
                "e": "rule",
                "id": rule_id,
                "t": now_iso(),
                "on": args.on,
                "pattern": args.match,
                "action": action,
                "reason": reason,
                "matched": matched,
            }
        ],
    )
    for key in matched:
        papers[key] = replace(
            papers[key], status=action, decision_reason=f"rule:{rule_id}: {reason}"
        )
    save_papers(session, papers)
    emit(
        {
            "rule": rule_id,
            "action": action,
            "matched": len(matched),
            "sample": matched[:5],
            "candidates_left": sum(
                paper.status == "candidate" for paper in papers.values()
            ),
        }
    )
    return 0


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


SORTS = {
    "citations": lambda paper: -(paper.cited_by_count or 0),
    "year": lambda paper: -(paper.year or 0),
    "key": lambda paper: paper.key,
}


def default_row(paper: Paper) -> dict[str, Any]:
    abstract = paper.abstract
    if abstract and len(abstract) > ABSTRACT_SHOW_LIMIT:
        abstract = abstract[:ABSTRACT_SHOW_LIMIT] + " [truncated]"
    return {
        "key": paper.key,
        "title": paper.title,
        "year": paper.year,
        "authors": list(paper.authors[:AUTHOR_SHOW_LIMIT]),
        "author_count": len(paper.authors),
        "venue": paper.venue,
        "citations": paper.cited_by_count,
        "status": paper.status,
        "read_level": paper.read_level,
        "abstract": abstract,
    }


def picked_fields(spec: str) -> list[str]:
    names = [name.strip() for name in spec.split(",") if name.strip()]
    unknown = sorted(set(names) - PAPER_FIELDS)
    if unknown:
        raise CommandError(
            f"unknown fields {unknown}; paper fields: {', '.join(sorted(PAPER_FIELDS))}"
        )
    return names


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item) for item in value)
    return str(value).replace("\t", " ").replace("\n", " ")


def cmd_show(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    papers = load_papers(session)
    missing: list[str] = []
    if args.keys:
        wanted = [key.strip() for key in args.keys.split(",") if key.strip()]
        missing = [key for key in wanted if key not in papers]
        matching = [papers[key] for key in wanted if key in papers]
    else:
        matching = [paper for paper in papers.values() if paper.status == args.status]
    if args.match:
        pattern = compile_match(args.match)
        matching = [
            paper for paper in matching if pattern.search(field_text(paper, args.on))
        ]
    matching.sort(key=SORTS[args.sort])
    total = len(matching)
    matching = matching[: args.limit]
    if missing:
        signal(f"no corpus paper for: {', '.join(missing)}")
    if total > len(matching):
        signal(f"{total - len(matching)} more matching papers not shown")
    if args.fields:
        names = picked_fields(args.fields)
        rows = [{name: getattr(paper, name) for name in names} for paper in matching]
    else:
        names = None
        rows = [default_row(paper) for paper in matching]
    if args.format == "tsv":
        header = names if names else (list(rows[0]) if rows else [])
        print("\t".join(header))
        for row in rows:
            print("\t".join(cell(row[name]) for name in header))
        return 0
    emit({"total": total, "papers": rows})
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
            "unextracted": unextracted(session.root, papers),
        }
    )
    return 0
