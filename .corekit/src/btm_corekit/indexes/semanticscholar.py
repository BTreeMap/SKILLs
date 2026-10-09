"""Semantic Scholar: the Academic Graph, with a citation graph of its own.

Keyless calls share one global pool with every unauthenticated caller and
are throttled under load, so a search can answer 429 while a single-paper
lookup still answers. A key, sent as `x-api-key`, buys one request per
second. The vendor publishes no keyless pace; one request per three seconds
measured clean for lookups, so that is the keyless interval, and `patient`
absorbs a 429 with bounded backoff.

Every call is one paced request plus at most two backoffs, linear in the
papers it decodes.
"""

from __future__ import annotations

import os
import urllib.parse
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import TypeVar

import httpx
from pydantic import Field

from btm_corekit.indexes.work import (
    ByArxiv,
    ByDoi,
    ByNative,
    Found,
    Ref,
    Window,
    Work,
    collapsed,
    normalize_arxiv_id,
    normalize_doi,
)
from btm_corekit.net.http import HTTP_NOT_FOUND, HTTP_TOO_MANY_REQUESTS
from btm_corekit.net.pace import ATTEMPTS, Pace, patient
from btm_corekit.net.wire import Upstream, json_body
from btm_corekit.report.channels import signal
from btm_corekit.report.errors import CommandError, UpstreamError

PAPER = "https://api.semanticscholar.org/graph/v1/paper"
PAPER_PAGE = "https://www.semanticscholar.org/paper/"

KEY_ENV = "BTM_SEMANTICSCHOLAR_KEY"
KEY_FORM = "semanticscholar.org/product/api"

KEYED_INTERVAL_SECONDS = 1.0
KEYLESS_INTERVAL_SECONDS = 3.0

FIELDS = ",".join(
    (
        "title",
        "abstract",
        "year",
        "venue",
        "citationCount",
        "publicationDate",
        "authors",
        "externalIds",
        "openAccessPdf",
    )
)
"""Exactly what a `Work` reads; `paperId` comes unasked."""

W = TypeVar("W", bound=Upstream)


@dataclass(frozen=True, slots=True)
class Keyed:
    key: str


@dataclass(frozen=True, slots=True)
class Keyless:
    """No key: the shared pool, throttled under load."""


Access = Keyed | Keyless

KEYED_PACE = Pace(KEYED_INTERVAL_SECONDS)
KEYLESS_PACE = Pace(KEYLESS_INTERVAL_SECONDS)


def access() -> Access:
    key = os.environ.get(KEY_ENV)
    return Keyed(key) if key else Keyless()


@cache
def _keyless_advisory() -> None:
    """Once per process; the cache is the guard."""
    signal(
        "no Semantic Scholar key: keyless calls share one pool throttled under "
        f"load, and search 429s first. Set {KEY_ENV} to a free key from "
        f"{KEY_FORM} for 1 request per second"
    )


def credential() -> tuple[Mapping[str, str], Pace]:
    """The header and the pace this run's access earns. Discloses a keyless
    run at its first call."""
    match access():
        case Keyed(key):
            return {"x-api-key": key}, KEYED_PACE
        case Keyless():
            _keyless_advisory()
            return {}, KEYLESS_PACE


def answer(
    model: type[W], client: httpx.Client, cap: int, url: str, params: Mapping[str, str]
) -> W:
    """One paced, patient call. A 429 that outlasts the backoff names the fix
    rather than the status."""
    headers, pace = credential()
    try:
        return patient(
            lambda: json_body(model, client, url, cap, params, headers=headers), pace
        )
    except UpstreamError as err:
        if err.status != HTTP_TOO_MANY_REQUESTS:
            raise
        fix = "retry later" if headers else f"set {KEY_ENV} (free at {KEY_FORM})"
        failure = UpstreamError(
            f"Semantic Scholar still throttles after {ATTEMPTS} tries: {fix}"
        )
        failure.status = err.status
        raise failure from err


class Author(Upstream):
    authorId: str | None = None
    name: str | None = None


class ExternalIds(Upstream):
    """Ids in other namespaces; `CorpusId` and the rest are ignored."""

    doi: str | None = Field(None, alias="DOI")
    arxiv: str | None = Field(None, alias="ArXiv")


class OpenAccessPdf(Upstream):
    """A closed paper carries this object with an empty `url`."""

    url: str | None = None
    status: str | None = None
    license: str | None = None


class Paper(Upstream):
    paperId: str | None = None
    title: str | None = None
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    citationCount: int | None = None
    publicationDate: str | None = None
    authors: tuple[Author, ...] = ()
    externalIds: ExternalIds | None = None
    openAccessPdf: OpenAccessPdf | None = None

    @property
    def names(self) -> tuple[str, ...]:
        named = (collapsed(author.name) for author in self.authors)
        return tuple(name for name in named if name)

    @property
    def doi(self) -> str | None:
        found: str | None = normalize_doi(
            self.externalIds.doi if self.externalIds else None
        )
        return found

    @property
    def arxiv_id(self) -> str | None:
        raw = self.externalIds.arxiv if self.externalIds else None
        found: str | None = normalize_arxiv_id(raw)
        return found

    @property
    def landing_url(self) -> str | None:
        """The DOI where one is registered, else the arXiv abs page, else the
        paper's own page here."""
        if doi := self.doi:
            return f"https://doi.org/{doi}"
        if arxiv_id := self.arxiv_id:
            return f"https://arxiv.org/abs/{arxiv_id}"
        return PAPER_PAGE + self.paperId if self.paperId else None

    @property
    def pdf_url(self) -> str | None:
        return (self.openAccessPdf.url or None) if self.openAccessPdf else None


class Page(Upstream):
    """A relevance-search page. The service documents `total` as a string and
    sends a number; both read as a count."""

    total: int | None = None
    offset: int | None = None
    next: int | None = None
    data: tuple[Paper, ...] = ()


class Cited(Upstream):
    citedPaper: Paper | None = None


class Citing(Upstream):
    citingPaper: Paper | None = None


class References(Upstream):
    """The papers a seed cites, each under `citedPaper`; no total is sent."""

    offset: int | None = None
    next: int | None = None
    data: tuple[Cited, ...] = ()


class Citations(Upstream):
    """The papers citing a seed, each under `citingPaper`; no total is sent."""

    offset: int | None = None
    next: int | None = None
    data: tuple[Citing, ...] = ()


def record(paper: Paper) -> Work:
    """One wire record across the boundary. The TLDR is never asked for, so
    `abstract` is the abstract alone."""
    return Work(
        title=collapsed(paper.title),
        authors=tuple(
            name for name in (collapsed(a.name) for a in paper.authors) if name
        ),
        year=paper.year,
        venue=collapsed(paper.venue),
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        openalex_id=None,
        cited_by=paper.citationCount,
        abstract=collapsed(paper.abstract),
        pdf_url=paper.pdf_url,
        landing_url=paper.landing_url,
        published=paper.publicationDate,
    )


def render(ref: Ref) -> str:
    """The `{paper_id}` path segment: a sha or `CorpusId:` as given, else the
    prefixed external id."""
    match ref:
        case ByNative(key):
            segment = key
        case ByDoi(doi):
            segment = f"DOI:{doi}"
        case ByArxiv(arxiv_id):
            segment = f"ARXIV:{arxiv_id}"
    return urllib.parse.quote(segment, safe="/:")


def year_range(window: Window) -> str:
    """`2016-2020`, `2010-`, or `-2015`: an open end stays empty."""
    return f"{window.from_year or ''}-{window.to_year or ''}"


def search(
    client: httpx.Client, cap: int, query: str, limit: int, window: Window
) -> Found:
    """One relevance page; the service caps `limit` at 100 and the whole
    ranking at 1,000."""
    params = {"query": query, "limit": str(limit), "fields": FIELDS}
    if window:
        params["year"] = year_range(window)
    page = answer(Page, client, cap, f"{PAPER}/search", params)
    return Found(total=page.total, works=tuple(map(record, page.data)))


def lookup(client: httpx.Client, cap: int, ref: Ref) -> Work | None:
    """One paper, or None where the service answers 404 for it."""
    url = f"{PAPER}/{render(ref)}"
    try:
        paper = answer(Paper, client, cap, url, {"fields": FIELDS})
    except UpstreamError:
        raise
    except CommandError as err:
        if err.status == HTTP_NOT_FOUND:
            return None
        raise
    return record(paper)


def references(client: httpx.Client, cap: int, ref: Ref, limit: int) -> Found:
    """The first `limit` papers the seed cites; the service caps it at 1,000."""
    url = f"{PAPER}/{render(ref)}/references"
    rows = answer(References, client, cap, url, {"fields": FIELDS, "limit": str(limit)})
    cited = (row.citedPaper for row in rows.data if row.citedPaper)
    return Found(total=None, works=tuple(map(record, cited)))


def citations(client: httpx.Client, cap: int, ref: Ref, limit: int) -> Found:
    """The first `limit` papers citing the seed; the service caps it at 1,000."""
    url = f"{PAPER}/{render(ref)}/citations"
    rows = answer(Citations, client, cap, url, {"fields": FIELDS, "limit": str(limit)})
    citing = (row.citingPaper for row in rows.data if row.citingPaper)
    return Found(total=None, works=tuple(map(record, citing)))
