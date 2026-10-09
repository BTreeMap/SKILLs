"""Corpus growth: opening a review, searching sources, snowballing citations."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from typing import Any

from btm_corekit import (
    INDEXES,
    ByArxiv,
    ByDoi,
    ByNative,
    CommandError,
    Model,
    NonEmpty,
    Ref,
    Window,
    append_jsonl,
    citations,
    content,
    count_lines,
    emit,
    normalize_arxiv_id,
    normalize_doi,
    now_iso,
    references,
    signal,
)
from btm_lit_review.constants import MAX_LIMIT, RESPONSE_CAP_BYTES
from btm_lit_review.corpus.paper import Paper, absorb, paper_aliases, paper_from
from btm_lit_review.corpus.sources import fetch
from btm_lit_review.http import client
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
from btm_lit_review.slots import FRAMING, QUERY


def record_fetch(
    session: Session,
    entry: dict[str, Any],
    fetched: list[Paper],
    total: int | None,
) -> None:
    """Shared tail of search and snowball: absorb, log, report. A total the
    index did not report is logged as null and never reads as truncation; a
    search skipped `offset` ranks, which the truncation check counts."""
    log_id = f"s{count_lines(session.log_path) + 1}"
    papers = load_papers(session)
    stamped = [paper.with_(found_by=(log_id,)) for paper in fetched]
    papers, new_count = absorb(papers, stamped)
    save_papers(session, papers)
    offset: int | None = entry.get("offset")  # a snowball has no ranks to skip
    reached = (offset or 0) + len(fetched)
    truncated = total is not None and total > reached
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
        skipped = f" after skipping {offset}" if offset else ""
        rerun = "" if offset is None else f", or rerun with --offset {reached}"
        signal(
            f"{total} matches upstream but only {len(fetched)} fetched{skipped}; "
            f"narrow the query or raise --limit (cap {MAX_LIMIT}){rerun}"
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
    framing = content(Framing, FRAMING, args)
    made = STORE.create(args.session)
    root, name = made.directory, made.name
    session = Session(root)
    root.mkdir(parents=True, exist_ok=True)
    protocol = Protocol(question=framing.question, level=args.level, created=now_iso())
    STORE.write_meta(root, protocol)
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
    asked = content(Query, QUERY, args).query
    session = open_session(args.session)
    protocol = load_protocol(session)
    require_criteria(protocol)
    limit = args.limit
    window = Window(args.from_year, args.to_year)
    fetched, total = fetch(args.source, asked, limit, window, args.offset)
    entry = {
        "command": "search",
        "source": args.source,
        "query": asked,
        "from_year": args.from_year,
        "to_year": args.to_year,
        "limit": limit,
        "offset": args.offset,
        "criteria_hash": criteria_hash(protocol),
    }
    record_fetch(session, entry, fetched, total)
    return 0


def _no_native(paper: Paper) -> str | None:
    return None


NATIVE_IDS: Mapping[str, Callable[[Paper], str | None]] = {
    "openalex": lambda paper: paper.openalex_id,
}
"""The index ids a Paper carries, by index; any other index is reached by
DOI or arXiv id."""


def resolve_ref(
    papers: Mapping[str, Paper], token: str, source: str
) -> tuple[str, Ref]:
    """(paper key, how `source` names it) for a key, DOI, or arXiv id: the
    index's own id where the paper carries one, else its DOI, else its arXiv
    id."""
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
    if native := NATIVE_IDS.get(source, _no_native)(paper):
        return key, ByNative(native)
    if paper.doi:
        return key, ByDoi(paper.doi)
    if paper.arxiv_id:
        return key, ByArxiv(paper.arxiv_id)
    raise CommandError(
        f"paper {key} has no {source} id, DOI, or arXiv id; snowball needs one"
    )


def cmd_snowball(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    protocol = load_protocol(session)
    require_criteria(protocol)
    limit = args.limit
    papers = load_papers(session)
    seed_key, ref = resolve_ref(papers, args.seed, args.source)
    walk = references if args.direction == "backward" else citations
    found = walk(INDEXES[args.source], client(), RESPONSE_CAP_BYTES, ref, limit)
    if args.direction == "backward" and not found.works and not found.total:
        signal(
            f"{args.source} lists no references for {seed_key}: upstream metadata "
            "gap; snowball another seed or read the paper's own reference list"
        )
    entry = {
        "command": "snowball",
        "source": args.source,
        "seed": seed_key,
        "direction": args.direction,
        "limit": limit,
        "criteria_hash": criteria_hash(protocol),
    }
    record_fetch(session, entry, list(map(paper_from, found.works)), found.total)
    return 0
