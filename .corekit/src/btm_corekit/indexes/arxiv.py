"""arXiv: preprints, over the Atom API.

The boundary here is the XML parse rather than a JSON decode, so the record
this module builds is already strict: an element the feed omits reads as
None on the way in, and nothing downstream sees a raw node.

Two facts about the feed are easy to get wrong and silent when wrong. A
paper's journal reference and its published DOI live in arXiv's own
namespace, not Atom's, so reading them as Atom yields nothing at all. And
arXiv ranks a fielded query far better than a bare phrase.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import httpx

from btm_corekit.indexes.work import Work, collapsed
from btm_corekit.net.http import get_bytes
from btm_corekit.records.models import Model

QUERY = "https://export.arxiv.org/api/query"

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"

MIN_INTERVAL_SECONDS = 3.0
"""arXiv's terms of use: no more than one request every three seconds from
one caller, counted across every machine that caller runs."""


@dataclass
class Pace:
    """The wait arXiv asks for, taken by the caller who owes it.

    An agent that fans out over a reading list would otherwise send a burst
    and be throttled for it, so the sleep belongs in the one place every
    request passes rather than in advice to the agent.
    """

    interval: float
    last: float = field(default=0.0)

    def wait(self) -> None:
        remaining = self.interval - (time.monotonic() - self.last)
        if remaining > 0:
            time.sleep(remaining)
        self.last = time.monotonic()


PACE = Pace(MIN_INTERVAL_SECONDS)


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


def feed(client: httpx.Client, cap: int, query: str, limit: int) -> Feed:
    """One search, after waiting out whatever the terms still owe."""
    PACE.wait()
    payload = get_bytes(
        client,
        QUERY,
        cap,
        {"search_query": fielded(query), "max_results": str(limit)},
    )
    return parse(payload)
