"""Argument surface: one query in, one JSON document of results out."""

from __future__ import annotations

import argparse
from collections.abc import Callable

import btm_search_web
from btm_corekit import (
    JSON,
    Commands,
    Parser,
    Required,
    add_slot,
    dump,
    emit,
    run_cli,
    signal,
    text,
)
from btm_search_web import sources
from btm_search_web.cache import clean, remember, remembered
from btm_search_web.constants import (
    DEFAULT_RESULTS,
    MAX_RESULTS,
    SCHOLAR_SOURCES,
    Scholar,
)
from btm_search_web.records import Result

QUERY = Required("query")


def answered(key: str, verb: str, query: str, find: Callable[[], list[Result]]) -> int:
    """Emit a verb's rows, reusing the cache when this query already ran."""
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
    if not rows:
        document["next"] = "widen the query, or try another verb"
    emit(document)
    return 0


def capped(limit: int) -> int:
    return max(1, min(limit, MAX_RESULTS))


def cmd_web(args: argparse.Namespace) -> int:
    limit, asked = capped(args.limit), text(QUERY, args)
    return answered(
        f"web:{limit}:{asked}", "web", asked, lambda: sources.web(asked, limit)
    )


def cmd_instant(args: argparse.Namespace) -> int:
    asked = text(QUERY, args)
    return answered(
        f"instant:{asked}", "instant", asked, lambda: sources.instant(asked)
    )


def cmd_wiki(args: argparse.Namespace) -> int:
    limit, asked = capped(args.limit), text(QUERY, args)
    return answered(
        f"wiki:{limit}:{asked}", "wiki", asked, lambda: sources.wiki(asked, limit)
    )


def cmd_scholar(args: argparse.Namespace) -> int:
    limit, asked = capped(args.limit), text(QUERY, args)
    source: Scholar = args.source
    return answered(
        f"scholar:{source}:{limit}:{asked}",
        f"scholar {source}",
        asked,
        lambda: sources.scholar(asked, limit, source),
    )


def cmd_fetch(args: argparse.Namespace) -> int:
    """One page's text, cached by URL in the record shape every verb caches."""
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
    emit({"verb": "fetch", "url": args.url, "chars": len(text), "text": text})
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    emit(clean())
    return 0


def add_query(parser: argparse.ArgumentParser, limited: bool = True) -> None:
    add_slot(parser, QUERY, "the search terms")
    if limited:
        parser.add_argument("--limit", type=int, default=DEFAULT_RESULTS)


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
        "--source", type=Scholar, choices=SCHOLAR_SOURCES, default=Scholar.OPENALEX
    )

    fetch = commands.add_parser("fetch", help="readable text of one page")
    fetch.set_defaults(func=cmd_fetch)
    fetch.add_argument("url", help="an http or https URL")

    cleaner = commands.add_parser("clean", help="drop the query cache, freeing space")
    cleaner.set_defaults(func=cmd_clean)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
