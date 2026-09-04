"""Screening and reporting: decisions in, corpus views out."""

from __future__ import annotations

import argparse
import heapq
from collections import Counter
from collections.abc import Mapping
from typing import Any

from pydantic import model_validator

from btm_corekit import (
    JSON,
    CommandError,
    Diagnostic,
    Item,
    Model,
    NonEmpty,
    append_jsonl,
    compile_match,
    content,
    digest,
    emit,
    now_iso,
    parse_model,
    read_batch,
    read_jsonl,
    rejection,
    signal,
)
from btm_lit_review.constants import (
    ABSTRACT_SHOW_LIMIT,
    AUTHOR_SHOW_LIMIT,
    Level,
    ReadLevel,
    Status,
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


def paper_field(paper: Paper, on: str) -> str:
    return str(getattr(paper, on) or "")


class Rule(Model):
    """One screening rule. The pattern is a regex and the reason is prose;
    both carry characters the shell rewrites, so both arrive on stdin.
    `NonEmpty` trims and rejects, which retires the hand-written check."""

    match: NonEmpty
    reason: NonEmpty


def cmd_screen(args: argparse.Namespace) -> int:
    """One rule screens many candidates; the record keeps the count honest."""
    rule = content(Rule, args.file, "the rule")
    session = open_session(args.session)
    require_criteria(load_protocol(session))
    pattern = compile_match(rule.match)
    reason = rule.reason
    action = Status.EXCLUDED if args.exclude else Status.INCLUDED
    papers = load_papers(session)
    matched = [
        key
        for key, paper in papers.items()
        if paper.status is Status.CANDIDATE
        and pattern.search(paper_field(paper, args.on))
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
                "pattern": rule.match,
                "action": action,
                "reason": reason,
                "matched": matched,
            }
        ],
    )
    for key in matched:
        papers[key] = papers[key].with_(
            status=action, decision_reason=f"rule:{rule_id}: {reason}"
        )
    save_papers(session, papers)
    emit(
        {
            "rule": rule_id,
            "action": action,
            "matched": len(matched),
            "sample": matched[:5],
            "candidates_left": sum(
                paper.status is Status.CANDIDATE for paper in papers.values()
            ),
        }
    )
    return 0


class Decision(Model):
    """One screening decision. An absent field keeps its value; an explicit
    null clears the reason. An exclusion states why in the same decision."""

    status: Status | None = None
    reason: str | None = None
    read_level: ReadLevel | None = None

    @model_validator(mode="after")
    def _sets_only_real_values(self) -> Decision:
        nulled = [
            name
            for name in ("status", "read_level")
            if name in self.model_fields_set and getattr(self, name) is None
        ]
        if nulled:
            raise ValueError(f"{', '.join(nulled)}: write a value, not null")
        if self.status is Status.EXCLUDED and not clean_text(self.reason):
            raise ValueError("an excluded paper carries the reason it was cut")
        return self


def parse_decision(
    key: str, decision: Any, papers: Mapping[str, Paper]
) -> dict[str, Any]:
    """One screening decision as the field updates `with_` applies.

    Only the keys the caller sent come back, so an omitted field keeps its
    value where a defaulted one would overwrite it.
    """
    if key not in papers:
        raise CommandError(f"decision names unknown paper key {key!r}")
    parsed = parse_model(Decision, decision, f"decision for {key}")
    sent = parsed.model_fields_set
    updates: dict[str, Any] = {}
    if "status" in sent:
        updates["status"] = parsed.status
    if "reason" in sent:
        updates["decision_reason"] = clean_text(parsed.reason)
    if "read_level" in sent:
        updates["read_level"] = parsed.read_level
    return updates


def cmd_update(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    decisions = read_batch(args.file)
    if isinstance(decisions, Diagnostic):
        emit(rejection([decisions], "papers"))
        return 1
    papers = load_papers(session)
    # Parse every decision before applying any, so a rejected batch leaves the
    # corpus exactly as it was rather than half updated.
    parsed = {
        key: parse_decision(key, decision, papers)
        for key, decision in decisions.items()
    }
    changed: Counter[str] = Counter()
    for key, updates in parsed.items():
        if (status := updates.get("status")) is not None:
            changed[status] += 1
        if (level := updates.get("read_level")) is not None:
            changed[f"read:{level}"] += 1
        papers[key] = papers[key].with_(**updates)
    save_papers(session, papers)
    emit({"applied": len(decisions), "changes": dict(changed)})
    return 0


SORTS = {
    "citations": lambda paper: -(paper.cited_by_count or 0),
    "year": lambda paper: -(paper.year or 0),
    "key": lambda paper: paper.key,
}


def default_row(paper: Paper) -> dict[str, JSON]:
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


def cmd_digest(args: argparse.Namespace) -> int:
    """The screening entry point: what kinds of candidate are in the corpus,
    with the rule that selects each kind.

    `show` costs the reader one row per candidate, which is the wrong price
    for a judgment whose real arity is the number of kinds. This projects the
    partition instead, so a few hundred candidates become a few dozen labels
    and each verdict is one `screen` away."""
    session = open_session(args.session)
    papers = load_papers(session)
    undecided = [paper for paper in papers.values() if paper.status == args.status]
    result = digest(
        [
            Item(
                key=paper.key,
                text=paper_field(paper, args.on),
                rank=float(paper.cited_by_count or 0),
            )
            for paper in undecided
        ],
        cap=args.clusters,
    )
    view = result.view()
    view["status"] = args.status
    view["next"] = (
        "judge each label, then cut or keep a whole cluster with "
        'screen --exclude and {"match": "<rule>", "reason": "..."} on stdin'
    )
    if result.residue_total > len(result.residue):
        signal(
            f"{result.residue_total - len(result.residue)} more unclustered "
            "candidates not shown; raise --clusters or screen the residue by hand"
        )
    emit(view)
    return 0


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
            paper for paper in matching if pattern.search(paper_field(paper, args.on))
        ]
    total = len(matching)
    matching = heapq.nsmallest(args.limit, matching, key=SORTS[args.sort])
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


# The band each level's shortlist is meant to land in. Leaving it is a
# judgment call, not an error, so the advisory names the band and the count
# and stops there: the agent decides whether to tighten criteria or disclose.
LEVEL_BANDS = {
    Level.LITE: (5, 10),
    Level.FULL: (10, 25),
    Level.ULTRA: (10, 40),
}


def next_step(
    criteria_ready: bool,
    searches: int,
    undecided: int,
    included: int,
    unextracted: list[str],
) -> str:
    """The cheapest legal next action, derived from live counts.

    Advisory, never a gate: which step is actually worth taking is the
    agent's call, and a session can legitimately revisit any phase. What the
    script owes is the arithmetic the agent would otherwise redo by hand."""
    if not criteria_ready:
        return "fill criteria.include and criteria.exclude in protocol.json"
    if not searches:
        return "run the first search"
    if undecided:
        return f"screen {undecided} undecided: digest, then screen per cluster"
    if not included:
        return "nothing is included yet; widen the search or revisit exclusions"
    if unextracted:
        return f"extract {len(unextracted)} included papers, then jot one record each"
    return "note findings and gaps, then brief"


def band_advisory(level: Level, included: int) -> str | None:
    band = LEVEL_BANDS.get(level)
    if band is None or not included:
        return None
    low, high = band
    span = f"the {level} band of {low} to {high}"
    if included < low:
        return f"{included} included is below {span}; search coverage may have failed"
    if included > high:
        return (
            f"{included} included is above {span}; tighten criteria or disclose "
            "the deviation in the report"
        )
    return None


def cmd_status(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    papers = load_papers(session)
    log = read_jsonl(session.log_path)
    by_status = Counter(paper.status for paper in papers.values())
    by_read = Counter(
        paper.read_level for paper in papers.values() if paper.status is Status.INCLUDED
    )
    current_hash = criteria_hash(protocol)
    logged_hashes = {entry.get("criteria_hash") for entry in log}
    if logged_hashes and logged_hashes != {current_hash}:
        signal(
            "criteria changed after searches ran; record the change in "
            "protocol.json amendments"
        )
    pending = unextracted(session.root, papers)
    undecided = by_status.get(Status.CANDIDATE, 0)
    included = by_status.get(Status.INCLUDED, 0)
    band = band_advisory(protocol.level, included)
    if band:
        signal(band)
    emit(
        {
            "question": protocol.question,
            "level": protocol.level,
            "criteria_ready": protocol.ready,
            "criteria_hash": current_hash,
            "searches": len(log),
            "papers": {status.value: n for status, n in by_status.items()},
            "included_read_levels": {level.value: n for level, n in by_read.items()},
            "undecided": undecided,
            "unextracted": pending,
            "next": next_step(protocol.ready, len(log), undecided, included, pending),
        }
    )
    return 0
