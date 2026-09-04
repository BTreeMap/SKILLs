"""Citation markers and the draft check they make mechanical.

Assignment is append-only and monotone: a paper keeps its number for the
life of the session, and a late inclusion extends the map, so renumbering
is unrepresentable.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from btm_corekit import CommandError, bracketed, emit, is_digits, signal, write_atomic
from btm_lit_review.constants import ReadLevel, Status
from btm_lit_review.notebook import (
    FindingRecord,
    finding_view,
    live,
    load_notebook,
)
from btm_lit_review.paper import Paper
from btm_lit_review.session import Session, load_papers, open_session


def load_markers(session: Session) -> dict[str, int]:
    path = session.citations_path
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def assign_markers(
    markers: Mapping[str, int], papers: Mapping[str, Paper]
) -> dict[str, int]:
    """Every included paper numbered, existing numbers untouched."""
    assigned = dict(markers)
    taken = max(assigned.values(), default=0)
    for key, paper in papers.items():
        if paper.status is Status.INCLUDED and key not in assigned:
            taken += 1
            assigned[key] = taken
    return assigned


def refresh_markers(session: Session, papers: Mapping[str, Paper]) -> dict[str, int]:
    markers = assign_markers(load_markers(session), papers)
    write_atomic(session.citations_path, json.dumps(markers, indent=2) + "\n")
    return markers


def marker_table(
    markers: Mapping[str, int], papers: Mapping[str, Paper]
) -> dict[str, dict[str, Any]]:
    return {
        f"[{number}]": {
            "key": key,
            "title": papers[key].title,
            "year": papers[key].year,
            "read_level": papers[key].read_level,
        }
        for key, number in sorted(markers.items(), key=lambda item: item[1])
        if key in papers
    }


def cite_check(
    text: str,
    markers: Mapping[str, int],
    papers: Mapping[str, Paper],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Pure verdict over a draft; O(draft + markers + findings)."""
    by_number = {number: key for key, number in markers.items()}
    used = {int(content) for content in bracketed(text) if is_digits(content)}
    problems = []
    for number in sorted(used):
        key = by_number.get(number)
        paper = papers.get(key) if key else None
        if paper is None:
            problems.append(f"[{number}] was never assigned; cite an assigned marker")
        elif paper.status is not Status.INCLUDED:
            problems.append(f"[{number}] cites {key}, which is {paper.status}")
        elif paper.read_level is ReadLevel.NONE:
            problems.append(f"[{number}] cites {key}, which is unread")
    unused = sorted(
        number
        for key, number in markers.items()
        if (paper := papers.get(key))
        and paper.status is Status.INCLUDED
        and number not in used
    )
    at_risk = [view for view in findings if view["state"] == "at-risk"]
    return {
        "citations": len(used),
        "problems": problems,
        "unused_included": [f"[{number}]" for number in unused],
        "at_risk_findings": at_risk,
    }


def cmd_cite_check(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    path = Path(args.draft).expanduser()
    if not path.is_file():
        raise CommandError(f"no draft at {path}")
    papers = load_papers(session)
    markers = refresh_markers(session, papers)
    findings = [
        finding_view(record, papers)
        for record in live(load_notebook(session), FindingRecord).values()
    ]
    report = cite_check(path.read_text(encoding="utf-8"), markers, papers, findings)
    report["markers"] = marker_table(markers, papers)
    emit(report)
    if report["problems"]:
        signal(f"{len(report['problems'])} citation problem(s); fix the draft")
        return 1
    return 0
