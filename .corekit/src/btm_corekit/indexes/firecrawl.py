"""The Firecrawl Research Index: about 43 million abstracts from arXiv,
PubMed, bioRxiv, and medRxiv, with full-text passages for a question.

Keyless calls work, capped per address per day with no published figure;
past the cap the service answers 429 until the reset. A daily cap is not a
rate, so nothing here paces; a 429 names the cap and the key instead. A key
rides as a bearer header.

The `/similar` endpoint is not a citation graph: its `citers` and
`references` modes expand from a seed and then rank by a free-text intent,
so what comes back is a relevance ranking over a neighbourhood, not the
list of works a paper cites. This index therefore offers no references and
no citations; `Similar` decodes the shape for a future caller.

Every call is one request, linear in the results or passages it decodes.
"""

from __future__ import annotations

import os
import urllib.parse
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
from typing import TypeVar

import httpx

from btm_corekit.indexes.work import (
    ByArxiv,
    ByDoi,
    ByNative,
    Found,
    Passage,
    Ref,
    Window,
    Work,
    collapsed,
    normalize_arxiv_id,
    normalize_doi,
)
from btm_corekit.net.http import HTTP_NOT_FOUND, HTTP_TOO_MANY_REQUESTS
from btm_corekit.net.wire import Upstream, json_body
from btm_corekit.report.channels import signal
from btm_corekit.report.errors import CommandError, UpstreamError

PAPERS = "https://api.firecrawl.dev/v2/search/research/papers"

KEY_ENV = "BTM_FIRECRAWL_KEY"

W = TypeVar("W", bound=Upstream)


def headers() -> dict[str, str]:
    """The credential, or nothing: keyless is a supported tier here."""
    key = os.environ.get(KEY_ENV)
    return {"Authorization": f"Bearer {key}"} if key else {}


@contextmanager
def _daily_cap() -> Iterator[None]:
    """429 here is the day's per-address allowance, and no backoff inside a
    session lifts it."""
    try:
        yield
    except UpstreamError as err:
        if err.status != HTTP_TOO_MANY_REQUESTS:
            raise
        failure = UpstreamError(
            "the Firecrawl Research Index's daily cap for this address is spent: "
            f"set {KEY_ENV} to a key from firecrawl.dev, or wait for the reset"
        )
        failure.status = err.status
        raise failure from err


def answer(
    model: type[W], client: httpx.Client, cap: int, url: str, params: Mapping[str, str]
) -> W:
    with _daily_cap():
        return json_body(model, client, url, cap, params, headers=headers())


class Paper(Upstream):
    """A search result and a paper's metadata in one record: a result adds
    `primaryId` and `score`, the paper endpoint adds `authors` as one
    comma-joined string, `categories`, and the dates."""

    paperId: str | None = None
    primaryId: str | None = None
    ids: dict[str, tuple[str, ...]] | None = None
    title: str | None = None
    abstract: str | None = None
    score: float | None = None
    authors: str | None = None
    categories: tuple[str, ...] = ()
    createdDate: str | None = None
    updateDate: str | None = None

    def namespaced(self, namespace: str) -> str | None:
        """The id in `namespace`: the preferred `primaryId` when it is that
        namespace's (`arxiv:1706.03762`), else the first id listed under it."""
        head, colon, rest = (self.primaryId or "").partition(":")
        if colon and head.lower() == namespace:
            return rest
        listed = (self.ids or {}).get(namespace, ())
        return listed[0] if listed else None

    @property
    def doi(self) -> str | None:
        found: str | None = normalize_doi(self.namespaced("doi"))
        return found

    @property
    def arxiv_id(self) -> str | None:
        found: str | None = normalize_arxiv_id(self.namespaced("arxiv"))
        return found

    @property
    def names(self) -> tuple[str, ...]:
        named = map(collapsed, (self.authors or "").split(","))
        return tuple(name for name in named if name)

    @property
    def created(self) -> str | None:
        """`createdDate` as an ISO day. The service sends an RFC 2822 stamp
        (`Wed, 11 May 2021 18:01:01 GMT`); an ISO one passes through."""
        if not self.createdDate:
            return None
        try:
            return parsedate_to_datetime(self.createdDate).date().isoformat()
        except (TypeError, ValueError):
            return self.createdDate

    @property
    def landing_url(self) -> str | None:
        if arxiv_id := self.arxiv_id:
            return f"https://arxiv.org/abs/{arxiv_id}"
        if doi := self.doi:
            return f"https://doi.org/{doi}"
        return None


class Results(Upstream):
    """What a search answers. `partial` means some of the index did not."""

    success: bool | None = None
    partial: bool | None = None
    results: tuple[Paper, ...] = ()


class Similar(Results):
    """What `/similar` answers: a ranked neighbourhood, never a graph."""

    poolSize: int | None = None
    truncated: bool | None = None
    note: str | None = None


class PassageRow(Upstream):
    text: str | None = None
    score: float | None = None


class Read(Upstream):
    """What the paper endpoint answers: the metadata, and with a `query` the
    passages ranked against it."""

    success: bool | None = None
    paper: Paper | None = None
    paperId: str | None = None
    query: str | None = None
    passages: tuple[PassageRow, ...] = ()


def record(paper: Paper) -> Work:
    """One wire record across the boundary. The index counts no citations
    and names no venue."""
    published = paper.created
    return Work(
        title=collapsed(paper.title),
        authors=paper.names,
        year=int(published[:4]) if published and published[:4].isdigit() else None,
        venue=None,
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        openalex_id=None,
        cited_by=None,
        abstract=collapsed(paper.abstract),
        pdf_url=None,
        landing_url=paper.landing_url,
        published=published,
    )


def render(ref: Ref) -> str:
    """The `{id}` path segment: a canonical numeric id as given, or a
    source id in the index's own spelling. A `/` inside a DOI is escaped so
    it stays one segment."""
    match ref:
        case ByNative(key):
            segment = key
        case ByDoi(doi):
            segment = f"doi:{doi}"
        case ByArxiv(arxiv_id):
            segment = f"arxiv:{arxiv_id}"
    return urllib.parse.quote(segment, safe=":")


def _checked(results: Results) -> Results:
    if results.success is False:
        raise UpstreamError("the Firecrawl Research Index answered success=false")
    if results.partial:
        signal("the Firecrawl Research Index answered partially; rerun for the rest")
    return results


def search(  # noqa: PLR0913, PLR0917 - the registry's Search signature
    client: httpx.Client,
    cap: int,
    query: str,
    limit: int,
    window: Window,
    offset: int = 0,
) -> Found:
    """One ranked list, `k` up to 500; the window becomes inclusive date
    bounds. No total is sent. The index takes no offset, so a span from rank
    `offset` asks for `offset + limit` and drops the head."""
    params = {"query": query, "k": str(offset + limit)}
    if window.from_year is not None:
        params["from"] = f"{window.from_year}-01-01"
    if window.to_year is not None:
        params["to"] = f"{window.to_year}-12-31"
    found = _checked(answer(Results, client, cap, PAPERS, params))
    return Found(total=None, works=tuple(map(record, found.results[offset:])))


def _read(
    client: httpx.Client, cap: int, ref: Ref, params: Mapping[str, str]
) -> Read | None:
    """The paper endpoint, or None where it answers 404."""
    try:
        return answer(Read, client, cap, f"{PAPERS}/{render(ref)}", params)
    except UpstreamError:
        raise
    except CommandError as err:
        if err.status == HTTP_NOT_FOUND:
            return None
        raise


def lookup(client: httpx.Client, cap: int, ref: Ref) -> Work | None:
    body = _read(client, cap, ref, {})
    return record(body.paper) if body and body.paper else None


def passages(
    client: httpx.Client, cap: int, ref: Ref, query: str | None, limit: int
) -> tuple[Passage, ...]:
    """Up to `limit` full-text passages ranked against `query` (at most 50).
    With no query the index reads nothing, so the abstract is the one
    passage, unscored. A paper the index does not hold is a refusal, so
    it never reads as a paper with nothing relevant in it."""
    asked = {} if query is None else {"query": query, "k": str(limit)}
    body = _read(client, cap, ref, asked)
    if body is None:
        raise CommandError(f"the Firecrawl Research Index holds no paper {render(ref)}")
    if query is None:
        abstract = collapsed(body.paper.abstract) if body.paper else None
        return (Passage(text=abstract, score=None),) if abstract else ()
    rows = (row for row in body.passages if row.text and row.text.strip())
    return tuple(Passage(text=row.text or "", score=row.score) for row in rows)
