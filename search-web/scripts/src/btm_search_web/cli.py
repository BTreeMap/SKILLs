"""Argument surface: one query or paper in, one JSON document out."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

import btm_search_web
from btm_corekit import (
    INDEXES,
    JSON,
    Commands,
    Optional,
    Parser,
    Required,
    add_slot,
    clean_cache,
    dump,
    emit,
    having,
    run_cli,
    signal,
    text,
    wire_limit,
)
from btm_search_web import sources
from btm_search_web.cache import remember, remembered
from btm_search_web.constants import (
    DEFAULT_PASSAGES,
    DEFAULT_RESULTS,
    MAX_RESULTS,
    THIN_CHARS,
)
from btm_search_web.records import Result

QUERY = Required("query")
QUESTION = Optional("query")
SCHOLAR_SOURCES = tuple(INDEXES)
PASSAGE_SOURCES = having("passages")


def answered(
    key: str,
    verb: str,
    query: str,
    find: Callable[[], list[Result]],
    limit: int | None = None,
) -> int:
    """Emit a verb's rows, reusing the cache when this query already ran.

    `limit` is the number actually asked of the upstream, so a clamped run
    reports what it ran rather than what was typed."""
    rows = remembered(key)
    if rows is None:
        rows = find()
        remember(key, rows)
    else:
        signal(f"cached: this {verb} ran before; clean drops the cache")
    document: dict[str, JSON] = {
        "verb": verb,
        "query": query,
        "results": [dump(row) for row in rows],
        "count": len(rows),
    }
    if limit is not None:
        document["limit"] = limit
    if not rows:
        document["next"] = "widen the query, or try another verb"
    emit(document)
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    limit, asked = args.limit, text(QUERY, args)
    return answered(
        f"web:{limit}:{asked}", "web", asked, lambda: sources.web(asked, limit), limit
    )


def cmd_instant(args: argparse.Namespace) -> int:
    asked = text(QUERY, args)
    return answered(
        f"instant:{asked}", "instant", asked, lambda: sources.instant(asked)
    )


def cmd_wiki(args: argparse.Namespace) -> int:
    limit, asked = args.limit, text(QUERY, args)
    return answered(
        f"wiki:{limit}:{asked}",
        "wiki",
        asked,
        lambda: sources.wiki(asked, limit),
        limit,
    )


def cmd_scholar(args: argparse.Namespace) -> int:
    limit, asked = args.limit, text(QUERY, args)
    source: str = args.source
    return answered(
        f"scholar:{source}:{limit}:{asked}",
        f"scholar {source}",
        asked,
        lambda: sources.scholar(asked, limit, source),
        limit,
    )


def cmd_passages(args: argparse.Namespace) -> int:
    """One paper's passages for a question, or its abstract with none."""
    asked = text(QUESTION, args)
    ref = sources.parse_ref(args.ref)
    found = sources.read(ref, asked, args.limit, args.source)
    document: dict[str, JSON] = {
        "verb": "passages",
        "ref": sources.spelled(ref),
        "source": args.source,
        "query": asked,
        "limit": args.limit,
        "passages": [dump(passage) for passage in found],
        "count": len(found),
    }
    if not found:
        document["next"] = "ask another question, or read the paper with fetch"
    emit(document)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """One page's text, cached by URL in the record shape every verb caches;
    with `--out`, the raw body written to a file and pinned by its digest,
    never cached, so the digest is always of what the server sent now."""
    if args.out is not None:
        target = Path(args.out).absolute()
        saved = sources.save(args.url, target)
        emit(
            {
                "verb": "fetch",
                "url": args.url,
                "path": str(target),
                "bytes": saved.size,
                "sha256": saved.sha256,
            }
        )
        return 0
    key = f"fetch:{args.url}"
    rows = remembered(key)
    if rows:
        signal("cached: this fetch ran before; clean drops the cache")
        text = rows[0].snippet
    else:
        text = sources.fetch(args.url)
        remember(
            key,
            [Result(title=args.url, url=args.url, source="fetch", snippet=text)],
        )
    if len(text) < THIN_CHARS:
        signal(
            f"thin: fetch extracted {len(text)} characters; the page is likely "
            "rendered by JavaScript, so its content lives elsewhere: look for "
            "a JSON or Markdown source (an API spec, a raw file) before "
            "reading the page as empty"
        )
    emit({"verb": "fetch", "url": args.url, "chars": len(text), "text": text})
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    emit(clean_cache("search-web"))
    return 0


def add_query(parser: argparse.ArgumentParser, limited: bool = True) -> None:
    add_slot(parser, QUERY, "the search terms")
    if limited:
        wire_limit(
            parser, what="rows to ask for", default=DEFAULT_RESULTS, cap=MAX_RESULTS
        )


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        prog="btm-search-web",
        description=btm_search_web.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands: Commands = parser.add_subparsers(dest="command", required=True)

    web = commands.add_parser("web", help="general web search across several engines")
    web.set_defaults(func=cmd_web)
    add_query(web)

    instant = commands.add_parser(
        "instant", help="DuckDuckGo's own definition or abstract for a term"
    )
    instant.set_defaults(func=cmd_instant)
    add_query(instant, limited=False)

    wiki = commands.add_parser("wiki", help="Wikipedia search with each page's summary")
    wiki.set_defaults(func=cmd_wiki)
    add_query(wiki)

    scholar = commands.add_parser("scholar", help="papers from a scholarly index")
    scholar.set_defaults(func=cmd_scholar)
    add_query(scholar)
    scholar.add_argument(
        "--source", choices=SCHOLAR_SOURCES, default=SCHOLAR_SOURCES[0]
    )

    reader = commands.add_parser(
        "passages", help="full-text passages of one paper for a question"
    )
    reader.set_defaults(func=cmd_passages)
    reader.add_argument("ref", help="a DOI, an arXiv id, or the index's own id")
    add_slot(reader, QUESTION, "the question the passages answer")
    reader.add_argument("--source", choices=PASSAGE_SOURCES, default=PASSAGE_SOURCES[0])
    wire_limit(
        reader, what="passages to ask for", default=DEFAULT_PASSAGES, cap=MAX_RESULTS
    )

    fetch = commands.add_parser("fetch", help="readable text of one page")
    fetch.set_defaults(func=cmd_fetch)
    fetch.add_argument("url", help="an http or https URL")
    fetch.add_argument(
        "--out",
        metavar="PATH",
        help="write the raw body to PATH, a new file, and report its bytes and "
        "SHA-256 instead of extracting text",
    )

    cleaner = commands.add_parser("clean", help="drop the query cache, freeing space")
    cleaner.set_defaults(func=cmd_clean)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
