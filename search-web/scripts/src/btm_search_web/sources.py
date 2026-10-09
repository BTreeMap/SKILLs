"""One function per backend, each returning the same result shape."""

from __future__ import annotations

import urllib.parse

import httpx
import trafilatura
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from btm_corekit import (
    INDEXES,
    CommandError,
    UpstreamError,
    Window,
    Work,
    client_for,
    get_bytes,
    json_body,
    search,
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


def client() -> httpx.Client:
    """Every request this skill owns goes through the kernel's client for it,
    memoized there, so the identity chain and the timeouts are the same on
    every call a process makes."""
    return client_for("search-web", read_timeout=TIMEOUT_SECONDS)


def web(query: str, limit: int) -> list[Result]:
    """A general search across whichever engines answer.

    The library falls back through its backends, so one rate-limited engine
    does not end the search. None of them is an official API: prefer the
    harness's own search tool wherever one exists.

    This is the one path that does not use `client`: DDGS owns its transport,
    so the shared identity chain, the shared timeouts, and the byte cap do
    not reach it. Replacing it would mean maintaining the scrape here.
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


def _hit(work: Work, source: str) -> Result:
    """One crossed index record as a result row. Written once: what differs
    between the indexes is upstream of here."""
    return Result(
        title=trimmed(work.names, TITLE_CHARS),
        url=work.landing_url or "",
        snippet=trimmed(work.abstract),
        source=source,
        published=work.published,
        doi=work.doi,
        year=work.year,
        cited_by=work.cited_by,
    )


def scholar(query: str, limit: int, source: Scholar) -> list[Result]:
    index = INDEXES[source.value]
    found = search(index, client(), RESPONSE_CAP_BYTES, query, limit, Window())
    return [_hit(work, index.name) for work in found.works]


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
