"""Corpus growth: opening a review, searching sources, snowballing citations."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    append_jsonl,
    band_signal,
    emit,
    is_pathlike,
    mint,
    now_iso,
    read_jsonl,
    signal,
    write_atomic,
)
from btm_lit_review.constants import MAX_LIMIT, OPENALEX_WORKS
from btm_lit_review.http import http_get_json
from btm_lit_review.paper import (
    Paper,
    absorb,
    normalize_arxiv_id,
    normalize_doi,
    paper_aliases,
)
from btm_lit_review.session import (
    STORE,
    Session,
    criteria_hash,
    load_papers,
    load_protocol,
    open_session,
    require_criteria,
    save_papers,
)
from btm_lit_review.sources import (
    fetch_arxiv,
    fetch_crossref,
    fetch_openalex,
    fetch_openalex_by_ids,
)
from btm_lit_review.upstream import paper_from_openalex


def record_fetch(
    session: Session,
    entry: dict[str, Any],
    fetched: list[Paper],
    total: int,
    limit: int,
) -> None:
    """Shared tail of search and snowball: absorb, log, report."""
    log_id = f"s{len(read_jsonl(session.log_path)) + 1}"
    papers = load_papers(session)
    stamped = [replace(paper, found_by=(log_id,)) for paper in fetched]
    papers, new_count = absorb(papers, stamped)
    save_papers(session, papers)
    truncated = total > len(fetched)
    entry.update(
        {
            "id": log_id,
            "time": now_iso(),
            "fetched": len(fetched),
            "new": new_count,
            "total_matches": total,
            "truncated": truncated,
        }
    )
    append_jsonl(session.log_path, [entry])
    if truncated:
        signal(
            f"{total} matches upstream but only {len(fetched)} fetched; "
            f"narrow the query or raise --limit (cap {MAX_LIMIT})"
        )
    emit({**entry, "corpus_size": len(papers)})


def cmd_init(args: argparse.Namespace) -> int:
    if is_pathlike(args.session):
        root = Path(args.session).expanduser()
        name = str(root)
    else:
        name = mint(args.session.split())
        if advice := band_signal(name.rsplit("-", 1)[0]):
            signal(advice)
        root = STORE.root() / name
    session = Session(root)
    if session.protocol_path.exists():
        raise CommandError(f"session already exists at {root}; refusing to overwrite")
    root.mkdir(parents=True, exist_ok=True)
    protocol = {
        "question": args.question,
        "level": args.level,
        "criteria": {"include": [], "exclude": []},
        "created": now_iso(),
        "amendments": [],
    }
    write_atomic(session.protocol_path, json.dumps(protocol, indent=2) + "\n")
    session.papers_path.touch()
    session.log_path.touch()
    emit(
        {
            "session": name,
            "dir": str(root.resolve()),
            "next": f"fill criteria lists in {session.protocol_path.resolve()}",
        }
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    require_criteria(protocol)
    limit = min(args.limit, MAX_LIMIT)
    if args.source == "openalex":
        fetched, total = fetch_openalex(args.query, limit, args.from_year, args.to_year)
    elif args.source == "arxiv":
        if args.from_year or args.to_year:
            signal("arxiv source ignores year bounds; filter after fetching")
        fetched, total = fetch_arxiv(args.query, limit)
        if total == 0 and ":" not in args.query:
            signal('arXiv matched nothing; retry with field syntax: all:"<phrase>"')
    else:
        fetched, total = fetch_crossref(args.query, limit, args.from_year, args.to_year)
    entry = {
        "command": "search",
        "source": args.source,
        "query": args.query,
        "from_year": args.from_year,
        "to_year": args.to_year,
        "limit": limit,
        "criteria_hash": criteria_hash(protocol),
    }
    record_fetch(session, entry, fetched, total, limit)
    return 0


def resolve_openalex_id(papers: Mapping[str, Paper], token: str) -> tuple[str, str]:
    """Return (paper key, OpenAlex work id) for a key, DOI, or arXiv id."""
    index = {
        alias: key for key, paper in papers.items() for alias in paper_aliases(paper)
    }
    key = token if token in papers else index.get(token)
    if key is None:
        doi = normalize_doi(token)
        arxiv_id = normalize_arxiv_id(token)
        key = index.get(f"doi:{doi}") or index.get(f"arxiv:{arxiv_id}")
    if key is None:
        raise CommandError(f"no corpus paper matches {token!r}; search for it first")
    paper = papers[key]
    if paper.openalex_id:
        return key, paper.openalex_id
    if paper.doi:
        work = http_get_json(f"{OPENALEX_WORKS}/doi:{paper.doi}")
        openalex_id = str(work.get("id") or "").rsplit("/", 1)[-1]
        if openalex_id:
            return key, openalex_id
    raise CommandError(
        f"paper {key} has no OpenAlex id or DOI; snowball needs one of them"
    )


def cmd_snowball(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    require_criteria(protocol)
    limit = min(args.limit, MAX_LIMIT)
    papers = load_papers(session)
    seed_key, work_id = resolve_openalex_id(papers, args.seed)
    if args.direction == "backward":
        work = http_get_json(f"{OPENALEX_WORKS}/{work_id}")
        referenced = [
            url.rsplit("/", 1)[-1] for url in work.get("referenced_works") or []
        ]
        total = len(referenced)
        if not referenced:
            signal(
                f"OpenAlex lists no references for {seed_key}: upstream metadata "
                "gap; snowball another seed or read the paper's own reference list"
            )
        fetched = fetch_openalex_by_ids(referenced[:limit])
    else:
        params = {"filter": f"cites:{work_id}", "per-page": str(limit)}
        body = http_get_json(OPENALEX_WORKS, params)
        total = (body.get("meta") or {}).get("count") or 0
        fetched = [paper_from_openalex(w) for w in body.get("results") or []]
    entry = {
        "command": "snowball",
        "seed": seed_key,
        "direction": args.direction,
        "limit": limit,
        "criteria_hash": criteria_hash(protocol),
    }
    record_fetch(session, entry, fetched, total, limit)
    return 0
