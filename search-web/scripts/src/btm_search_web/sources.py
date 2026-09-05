"""One function per backend, each returning the same result shape."""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from functools import cache

import httpx
import trafilatura
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from btm_corekit import (
    CommandError,
    UpstreamError,
    Work,
    arxiv,
    build_client,
    crossref,
    get_bytes,
    json_body,
    openalex,
)
from btm_search_web.constants import (
    APP,
    INSTANT_ANSWER,
    PAGE_CAP_BYTES,
    RESPONSE_CAP_BYTES,
    TIMEOUT_SECONDS,
    TITLE_CHARS,
    TOPIC_CHARS,
    WIKI_SEARCH,
    WIKI_SUMMARY,
    Scholar,
)
from btm_search_web.records import Result, trimmed
from btm_search_web.upstream import InstantAnswer, WikiSearch, WikiSummary


@cache
def client() -> httpx.Client:
    return build_client("search-web", read_timeout=TIMEOUT_SECONDS)


def web(query: str, limit: int) -> list[Result]:
    """A general search across whichever engines answer.

    The library falls back through its backends, so one rate-limited engine
    does not end the search. None of them is an official API: prefer the
    harness's own search tool wherever one exists.
    """
    try:
        rows = DDGS().text(query, max_results=limit)
    except DDGSException as err:
        raise UpstreamError(f"no search backend answered: {err}") from err
    return [
        Result(
            title=trimmed(str(row.get("title") or "")) or "(untitled)",
            url=str(row.get("href") or ""),
            snippet=trimmed(str(row.get("body") or "")),
            source="web",
        )
        for row in rows
    ]


def instant(query: str) -> list[Result]:
    """DuckDuckGo's own instant answers: a definition or an abstract, never a
    ranked result list. Official and keyless; `t` names the caller as its
    terms ask."""
    body = json_body(
        InstantAnswer,
        client(),
        INSTANT_ANSWER,
        RESPONSE_CAP_BYTES,
        {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1", "t": APP},
    )
    found: list[Result] = []
    if says := body.says:
        found.append(
            Result(
                title=body.heading or query,
                url=body.source_url,
                snippet=trimmed(says),
                source="instant",
            )
        )
    found += [
        Result(
            title=trimmed(topic.text, TOPIC_CHARS),
            url=topic.url or "",
            snippet=trimmed(topic.text),
            source="instant",
        )
        for topic in body.topics
        if topic.text
    ]
    return found


def wiki(query: str, limit: int) -> list[Result]:
    """Wikipedia's own search, then each page's summary."""
    body = json_body(
        WikiSearch,
        client(),
        WIKI_SEARCH,
        RESPONSE_CAP_BYTES,
        {"q": query, "limit": str(limit)},
    )
    found: list[Result] = []
    for page in body.pages:
        summary = (
            json_body(
                WikiSummary,
                client(),
                WIKI_SUMMARY + urllib.parse.quote(page.key),
                RESPONSE_CAP_BYTES,
            )
            if page.key
            else WikiSummary()
        )
        found.append(
            Result(
                title=page.title or page.key or "(untitled)",
                url=summary.url or f"https://en.wikipedia.org/wiki/{page.key}",
                snippet=trimmed(summary.extract or page.description),
                source="wiki",
            )
        )
    return found


def _hit(work: Work, source: Scholar) -> Result:
    """One crossed index record as a result row. Written once: what differs
    between the indexes is upstream of here."""
    return Result(
        title=trimmed(work.names, TITLE_CHARS),
        url=work.landing_url or "",
        snippet=trimmed(work.abstract),
        source=source.value,
        published=work.published,
        doi=work.doi,
        year=work.year,
        cited_by=work.cited_by,
    )


def _openalex(query: str, limit: int) -> list[Result]:
    page = openalex.page(
        client(), RESPONSE_CAP_BYTES, {"search": query, "per-page": str(limit)}
    )
    return [_hit(openalex.record(work), Scholar.OPENALEX) for work in page.results]


def _crossref(query: str, limit: int) -> list[Result]:
    message = crossref.page(
        client(), RESPONSE_CAP_BYTES, {"query": query, "rows": str(limit)}
    )
    return [_hit(crossref.record(item), Scholar.CROSSREF) for item in message.items]


def _arxiv(query: str, limit: int) -> list[Result]:
    feed = arxiv.feed(client(), RESPONSE_CAP_BYTES, query, limit)
    return [_hit(arxiv.record(entry), Scholar.ARXIV) for entry in feed.entries]


SCHOLARS: dict[Scholar, Callable[[str, int], list[Result]]] = {
    Scholar.OPENALEX: _openalex,
    Scholar.CROSSREF: _crossref,
    Scholar.ARXIV: _arxiv,
}


def scholar(query: str, limit: int, source: Scholar) -> list[Result]:
    return SCHOLARS[source](query, limit)


def fetch(url: str) -> str:
    """The readable text of one page.

    A PDF is refused rather than mangled: `/read-pdf` extracts those.
    """
    if not url.startswith(("http://", "https://")):
        raise CommandError(f"fetch takes an http or https URL; got {url!r}")
    payload = get_bytes(client(), url, PAGE_CAP_BYTES)
    if payload[:5] == b"%PDF-":
        raise CommandError(f"{url} is a PDF; read it with /read-pdf")
    text = trafilatura.extract(payload.decode("utf-8", "replace"))
    if not text:
        raise CommandError(
            f"no readable article found at {url}; the page may be a listing, "
            "a paywall, or rendered by JavaScript"
        )
    return str(text)
