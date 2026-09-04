"""One function per backend, each returning the same result shape."""

from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from functools import cache
from typing import Any

import httpx
import trafilatura
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from btm_corekit import (
    CommandError,
    UpstreamError,
    build_client,
    get_bytes,
    openalex_query,
)
from btm_search_web.constants import (
    APP,
    ARXIV_NS,
    ARXIV_QUERY,
    ATOM,
    CROSSREF_WORKS,
    INSTANT_ANSWER,
    OPENALEX_WORKS,
    PAGE_CAP_BYTES,
    RESPONSE_CAP_BYTES,
    TIMEOUT_SECONDS,
    WIKI_SEARCH,
    WIKI_SUMMARY,
    Scholar,
)
from btm_search_web.records import Result, trimmed


@cache
def client() -> httpx.Client:
    return build_client("search-web", read_timeout=TIMEOUT_SECONDS)


def _json(url: str, params: Mapping[str, str] | None = None) -> Any:
    payload = get_bytes(client(), url, RESPONSE_CAP_BYTES, params)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as err:
        raise UpstreamError(f"non-JSON response from {url}") from err


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
    body = _json(
        INSTANT_ANSWER,
        {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1", "t": APP},
    )
    found: list[Result] = []
    abstract = body.get("AbstractText") or body.get("Answer") or ""
    if abstract:
        found.append(
            Result(
                title=body.get("Heading") or query,
                url=body.get("AbstractURL") or "",
                snippet=trimmed(str(abstract)),
                source="instant",
            )
        )
    for topic in body.get("RelatedTopics") or []:
        text = topic.get("Text") if isinstance(topic, dict) else None
        if not text:
            continue
        found.append(
            Result(
                title=trimmed(str(text), 80),
                url=str(topic.get("FirstURL") or ""),
                snippet=trimmed(str(text)),
                source="instant",
            )
        )
    return found


def wiki(query: str, limit: int) -> list[Result]:
    """Wikipedia's own search, then each page's summary."""
    body = _json(WIKI_SEARCH, {"q": query, "limit": str(limit)})
    found: list[Result] = []
    for page in body.get("pages") or []:
        key = str(page.get("key") or "")
        summary = _json(WIKI_SUMMARY + urllib.parse.quote(key)) if key else {}
        found.append(
            Result(
                title=str(page.get("title") or key or "(untitled)"),
                url=(summary.get("content_urls") or {})
                .get("desktop", {})
                .get("page", f"https://en.wikipedia.org/wiki/{key}"),
                snippet=trimmed(summary.get("extract") or page.get("description")),
                source="wiki",
            )
        )
    return found


def _openalex(query: str, limit: int) -> list[Result]:
    body = _json(
        OPENALEX_WORKS, openalex_query({"search": query, "per-page": str(limit)})
    )
    found = []
    for work in body.get("results") or []:
        doi = str(work.get("doi") or "").removeprefix("https://doi.org/")
        found.append(
            Result(
                title=trimmed(work.get("display_name"), 300) or "(untitled)",
                url=work.get("doi") or work.get("id") or "",
                snippet=trimmed(_abstract(work.get("abstract_inverted_index"))),
                source="openalex",
                doi=doi or None,
                year=work.get("publication_year"),
                cited_by=work.get("cited_by_count"),
            )
        )
    return found


def _abstract(inverted: Mapping[str, list[int]] | None) -> str:
    """OpenAlex stores an abstract as a word-to-positions index."""
    if not inverted:
        return ""
    places = sorted(
        (position, word) for word, spots in inverted.items() for position in spots
    )
    return " ".join(word for _, word in places)


def _crossref(query: str, limit: int) -> list[Result]:
    message = (
        _json(CROSSREF_WORKS, {"query": query, "rows": str(limit)}).get("message") or {}
    )
    found = []
    for item in message.get("items") or []:
        found.append(
            Result(
                title=trimmed(" ".join(item.get("title") or []), 300) or "(untitled)",
                url=str(item.get("URL") or ""),
                snippet=trimmed(item.get("abstract")),
                source="crossref",
                doi=item.get("DOI"),
                year=((item.get("issued") or {}).get("date-parts") or [[None]])[0][0],
                cited_by=item.get("is-referenced-by-count"),
            )
        )
    return found


def _arxiv(query: str, limit: int) -> list[Result]:
    """arXiv ranks a fielded query far better than a bare phrase."""
    fielded = query if ":" in query else f'all:"{query}"'
    payload = get_bytes(
        client(),
        ARXIV_QUERY,
        RESPONSE_CAP_BYTES,
        {"search_query": fielded, "max_results": str(limit)},
    )
    root = ET.fromstring(payload)
    found = []
    for entry in root.findall(ATOM + "entry"):
        published = (entry.findtext(ATOM + "published") or "")[:10]
        doi = entry.findtext(ARXIV_NS + "doi")
        found.append(
            Result(
                title=trimmed(entry.findtext(ATOM + "title"), 300) or "(untitled)",
                url=entry.findtext(ATOM + "id") or "",
                snippet=trimmed(entry.findtext(ATOM + "summary")),
                source="arxiv",
                published=published or None,
                doi=doi,
                year=int(published[:4]) if published[:4].isdigit() else None,
            )
        )
    return found


SCHOLARS = {
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
