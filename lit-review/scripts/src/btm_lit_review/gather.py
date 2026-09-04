"""Corpus growth: opening a review, searching sources, snowballing citations."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from collections.abc import Mapping
from typing import Any

from btm_corekit import (
    CommandError,
    Model,
    NonEmpty,
    append_jsonl,
    content,
    count_lines,
    dump,
    emit,
    now_iso,
    openalex_page,
    openalex_work,
    signal,
    write_atomic,
)
from btm_lit_review.constants import MAX_LIMIT, RESPONSE_CAP_BYTES
from btm_lit_review.http import client
from btm_lit_review.paper import (
    Paper,
    absorb,
    normalize_arxiv_id,
    normalize_doi,
    paper_aliases,
)
from btm_lit_review.session import (
    STORE,
    Protocol,
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
    log_id = f"s{count_lines(session.log_path) + 1}"
    papers = load_papers(session)
    stamped = [paper.with_(found_by=(log_id,)) for paper in fetched]
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


class Framing(Model):
    """The review's question. Prose, so it arrives on stdin."""

    question: NonEmpty


class Query(Model):
    """One search string. arXiv's field syntax is `all:"<phrase>"`, whose
    quotes the shell would strip before argparse ever saw them."""

    query: NonEmpty


def cmd_init(args: argparse.Namespace) -> int:
    framing = content(Framing, args.file, "the framing")
    made = STORE.create(args.session)
    root, name = made.directory, made.name
    session = Session(root)
    root.mkdir(parents=True, exist_ok=True)
    protocol = Protocol(question=framing.question, level=args.level, created=now_iso())
    write_atomic(session.protocol_path, json.dumps(dump(protocol), indent=2) + "\n")
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
    asked = content(Query, args.file, "the query").query
    session = open_session(args.session)
    protocol = load_protocol(session)
    require_criteria(protocol)
    limit = min(args.limit, MAX_LIMIT)
    if args.source == "openalex":
        fetched, total = fetch_openalex(asked, limit, args.from_year, args.to_year)
    elif args.source == "arxiv":
        if args.from_year or args.to_year:
            signal("arxiv source ignores year bounds; filter after fetching")
        fetched, total = fetch_arxiv(asked, limit)
        if total == 0 and ":" not in asked:
            signal('arXiv matched nothing; retry with field syntax: all:"<phrase>"')
    else:
        fetched, total = fetch_crossref(asked, limit, args.from_year, args.to_year)
    entry = {
        "command": "search",
        "source": args.source,
        "query": asked,
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
        work = openalex_work(
            client(), RESPONSE_CAP_BYTES, f"doi:{urllib.parse.quote(paper.doi)}"
        )
        if work.key:
            return key, work.key
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
        work = openalex_work(client(), RESPONSE_CAP_BYTES, work_id)
        referenced = [url.rsplit("/", 1)[-1] for url in work.referenced_works]
        total = len(referenced)
        if not referenced:
            signal(
                f"OpenAlex lists no references for {seed_key}: upstream metadata "
                "gap; snowball another seed or read the paper's own reference list"
            )
        fetched = fetch_openalex_by_ids(referenced[:limit])
    else:
        page = openalex_page(
            client(),
            RESPONSE_CAP_BYTES,
            {"filter": f"cites:{work_id}", "per-page": str(limit)},
        )
        total = page.meta.count
        fetched = [paper_from_openalex(work) for work in page.results]
    entry = {
        "command": "snowball",
        "seed": seed_key,
        "direction": args.direction,
        "limit": limit,
        "criteria_hash": criteria_hash(protocol),
    }
    record_fetch(session, entry, fetched, total, limit)
    return 0
