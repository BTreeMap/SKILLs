"""arXiv: preprints, over the Atom API.

The boundary here is the XML parse rather than a JSON decode, so the record
this module builds is already strict: an element the feed omits reads as
None on the way in, and nothing downstream sees a raw node.

Two facts about the feed are easy to get wrong and silent when wrong. A
paper's journal reference and its published DOI live in arXiv's own
namespace, not Atom's, so reading them as Atom yields nothing at all. And
arXiv ranks a fielded query far better than a bare phrase.

Each call is one paced request, linear in the entries it parses.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from btm_corekit.indexes.work import (
    ARXIV_DOI_PREFIX,
    ByArxiv,
    ByDoi,
    ByNative,
    Found,
    Ref,
    Window,
    Work,
    collapsed,
    normalize_arxiv_id,
)
from btm_corekit.net.http import get_bytes
from btm_corekit.net.pace import Pace
from btm_corekit.records.models import Model
from btm_corekit.report.channels import signal

QUERY = "https://export.arxiv.org/api/query"

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"

MIN_INTERVAL_SECONDS = 3.0
"""arXiv's terms of use: no more than one request every three seconds from
one caller, counted across every machine that caller runs."""

PACE = Pace(MIN_INTERVAL_SECONDS)
"""Every request this process sends arXiv waits here, so a fan-out over a
reading list cannot burst."""


class Entry(Model):
    """One paper in the feed."""

    id: str | None = None
    title: str | None = None
    summary: str | None = None
    published: str | None = None
    journal_ref: str | None = None
    doi: str | None = None
    authors: tuple[str, ...] = ()
    pdf_url: str | None = None


class Feed(Model):
    total: int | None = None
    entries: tuple[Entry, ...] = ()


def fielded(query: str) -> str:
    """arXiv ranks `all:"exact phrase"` far better than the bare phrase, and
    a query that already names a field is left as the caller wrote it."""
    return query if ":" in query else f'all:"{query}"'


def _entry(node: ET.Element) -> Entry:
    def atom(tag: str) -> str | None:
        return collapsed(node.findtext(ATOM + tag))

    names = (name.text for name in node.findall(f"{ATOM}author/{ATOM}name"))
    return Entry(
        id=atom("id"),
        title=atom("title"),
        summary=atom("summary"),
        published=atom("published"),
        journal_ref=collapsed(node.findtext(ARXIV + "journal_ref")),
        doi=collapsed(node.findtext(ARXIV + "doi")),
        authors=tuple(name for name in map(collapsed, names) if name),
        pdf_url=next(
            (
                link.get("href")
                for link in node.findall(ATOM + "link")
                if link.get("title") == "pdf"
            ),
            None,
        ),
    )


def parse(payload: bytes) -> Feed:
    """The feed, as records. Pure: the request is the caller's."""
    root = ET.fromstring(payload)
    total = collapsed(root.findtext(OPENSEARCH + "totalResults")) or ""
    return Feed(
        total=int(total) if total.isdigit() else None,
        entries=tuple(map(_entry, root.findall(ATOM + "entry"))),
    )


def record(entry: Entry) -> Work:
    """One wire record across the boundary."""
    stamped = entry.published or ""
    return Work(
        title=entry.title,
        authors=entry.authors,
        year=int(stamped[:4]) if stamped[:4].isdigit() else None,
        venue=entry.journal_ref,
        doi=entry.doi,
        arxiv_id=entry.id,
        openalex_id=None,
        cited_by=None,
        abstract=entry.summary,
        pdf_url=entry.pdf_url,
        landing_url=entry.id,
        published=entry.published,
    )


def feed(
    client: httpx.Client, cap: int, query: str, limit: int, start: int = 0
) -> Feed:
    """One search from rank `start`, after waiting out whatever the terms
    still owe."""
    PACE.wait()
    params = {"search_query": fielded(query), "max_results": str(limit)}
    if start:
        params["start"] = str(start)
    return parse(get_bytes(client, QUERY, cap, params))


def search(  # noqa: PLR0913, PLR0917 - the registry's Search signature
    client: httpx.Client,
    cap: int,
    query: str,
    limit: int,
    window: Window,
    offset: int = 0,
) -> Found:
    """One ranked feed from rank `offset`. The API has no date filter, so the
    window is the registry's to disclaim; an empty answer to a bare phrase
    says how to retry."""
    answer = feed(client, cap, query, limit, offset)
    if not answer.total and ":" not in query:
        signal('arXiv matched nothing; retry with field syntax: all:"<phrase>"')
    return Found(total=answer.total, works=tuple(map(record, answer.entries)))


def _arxiv_id(ref: Ref) -> str | None:
    """arXiv's native id is the arXiv id; a DOI names a paper here only when
    it is the one arXiv registered."""
    parsed: str | None
    match ref:
        case ByArxiv(arxiv_id):
            parsed = arxiv_id
        case ByNative(raw):
            parsed = normalize_arxiv_id(raw)
        case ByDoi(doi):
            registered = doi.startswith(ARXIV_DOI_PREFIX)
            parsed = normalize_arxiv_id(doi) if registered else None
    return parsed


def lookup(client: httpx.Client, cap: int, ref: Ref) -> Work | None:
    """One entry by `id_list`. An unknown id comes back as an error entry
    whose id is no arXiv id, which reads as absence."""
    arxiv_id = _arxiv_id(ref)
    if arxiv_id is None:
        return None
    PACE.wait()
    payload = get_bytes(client, QUERY, cap, {"id_list": arxiv_id, "max_results": "1"})
    entry = next(iter(parse(payload).entries), None)
    work = record(entry) if entry else None
    return work if work and work.arxiv_id else None
