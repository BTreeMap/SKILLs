"""One function per backend, each returning the same result shape."""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Callable, Mapping
from functools import cache
from typing import TypeVar

import httpx
import trafilatura
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from btm_corekit import (
    CommandError,
    Model,
    UpstreamError,
    arxiv_feed,
    build_client,
    crossref_page,
    get_bytes,
    openalex_page,
    parse_model,
)
from btm_search_web.constants import (
    APP,
    INSTANT_ANSWER,
    PAGE_CAP_BYTES,
    RESPONSE_CAP_BYTES,
    TIMEOUT_SECONDS,
    WIKI_SEARCH,
    WIKI_SUMMARY,
    Scholar,
)
from btm_search_web.records import Result, trimmed
from btm_search_web.upstream import InstantAnswer, WikiSearch, WikiSummary

U = TypeVar("U", bound=Model)


@cache
def client() -> httpx.Client:
    return build_client("search-web", read_timeout=TIMEOUT_SECONDS)


def _read(model: type[U], url: str, params: Mapping[str, str] | None = None) -> U:
    """One upstream response, decoded into the record this skill reads."""
    payload = get_bytes(client(), url, RESPONSE_CAP_BYTES, params)
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as err:
        raise UpstreamError(f"non-JSON response from {url}") from err
    return parse_model(model, body, f"response from {url}")


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
    body = _read(
        InstantAnswer,
        INSTANT_ANSWER,
        {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1", "t": APP},
    )
    found: list[Result] = []
    if abstract := body.abstract or body.answer:
        found.append(
            Result(
                title=body.heading or query,
                url=body.abstract_url,
                snippet=trimmed(abstract),
                source="instant",
            )
        )
    found += [
        Result(
            title=trimmed(topic.text, 80),
            url=topic.url,
            snippet=trimmed(topic.text),
            source="instant",
        )
        for topic in body.topics
        if topic.text
    ]
    return found


def wiki(query: str, limit: int) -> list[Result]:
    """Wikipedia's own search, then each page's summary."""
    body = _read(WikiSearch, WIKI_SEARCH, {"q": query, "limit": str(limit)})
    found: list[Result] = []
    for page in body.pages:
        summary = (
            _read(WikiSummary, WIKI_SUMMARY + urllib.parse.quote(page.key))
            if page.key
            else WikiSummary()
        )
        found.append(
            Result(
                title=page.title or page.key or "(untitled)",
                url=summary.content_urls.desktop.page
                or f"https://en.wikipedia.org/wiki/{page.key}",
                snippet=trimmed(summary.extract or page.description),
                source="wiki",
            )
        )
    return found


def _openalex(query: str, limit: int) -> list[Result]:
    page = openalex_page(
        client(), RESPONSE_CAP_BYTES, {"search": query, "per-page": str(limit)}
    )
    return [
        Result(
            title=trimmed(work.display_name, 300) or "(untitled)",
            url=work.doi or work.id,
            snippet=trimmed(work.abstract),
            source="openalex",
            doi=(work.doi or "").removeprefix("https://doi.org/") or None,
            year=work.publication_year,
            cited_by=work.cited_by_count,
        )
        for work in page.results
    ]


def _crossref(query: str, limit: int) -> list[Result]:
    message = crossref_page(
        client(), RESPONSE_CAP_BYTES, {"query": query, "rows": str(limit)}
    )
    return [
        Result(
            title=trimmed(" ".join(item.title), 300) or "(untitled)",
            url=item.url,
            snippet=trimmed(item.abstract),
            source="crossref",
            doi=item.doi,
            year=item.issued.year,
            cited_by=item.cited_by,
        )
        for item in message.items
    ]


def _arxiv(query: str, limit: int) -> list[Result]:
    feed = arxiv_feed(client(), RESPONSE_CAP_BYTES, query, limit)
    return [
        Result(
            title=trimmed(entry.title, 300) or "(untitled)",
            url=entry.id,
            snippet=trimmed(entry.summary),
            source="arxiv",
            published=entry.published[:10] or None,
            doi=entry.doi,
            year=int(entry.published[:4]) if entry.published[:4].isdigit() else None,
        )
        for entry in feed.entries
    ]


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
