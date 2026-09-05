"""Crossref: the registration agency's own record for a DOI.

Keyless, and still routed to the polite pool by the contact the origin
carries. What it returns is registration metadata, so an abstract and an
author list are frequently absent where a DOI is not.

Two endpoints answer under one key. A search puts a list of items under
`message`; a single DOI puts the item itself there. They are different
shapes, so they are different records.
"""

from __future__ import annotations

from collections.abc import Mapping

import httpx
from pydantic import Field

from btm_corekit.indexes.work import Work, collapsed
from btm_corekit.net.origin import polite_params
from btm_corekit.net.wire import Upstream, json_body
from btm_corekit.report.errors import CommandError, UpstreamError
from btm_corekit.text import strip_tags

WORKS = "https://api.crossref.org/works"


def date_filter(from_year: int | None, to_year: int | None) -> str:
    parts = []
    if from_year:
        parts.append(f"from-pub-date:{from_year}-01-01")
    if to_year:
        parts.append(f"until-pub-date:{to_year}-12-31")
    return ",".join(parts)


class Author(Upstream):
    given: str | None = None
    family: str | None = None

    @property
    def name(self) -> str | None:
        """A record may carry either half alone, and an organisation carries
        neither."""
        return collapsed(" ".join(part for part in (self.given, self.family) if part))


class Issued(Upstream):
    date_parts: tuple[tuple[int | None, ...], ...] = Field((), alias="date-parts")

    @property
    def year(self) -> int | None:
        """Crossref writes a date it does not know as `[[null]]`: the outer
        list is present and the year inside it is not."""
        head = self.date_parts[0] if self.date_parts else ()
        return head[0] if head else None


class Item(Upstream):
    """One registered record. A title and a venue arrive as lists because a
    work may carry more than one of each."""

    title: tuple[str, ...] = ()
    container_title: tuple[str, ...] = Field((), alias="container-title")
    author: tuple[Author, ...] = ()
    doi: str | None = Field(None, alias="DOI")
    url: str | None = Field(None, alias="URL")
    abstract: str | None = None
    issued: Issued | None = None
    cited_by: int | None = Field(None, alias="is-referenced-by-count")

    @property
    def authors(self) -> tuple[str, ...]:
        return tuple(name for name in (person.name for person in self.author) if name)

    @property
    def venue(self) -> str | None:
        return collapsed(" ".join(self.container_title))

    @property
    def year(self) -> int | None:
        return self.issued.year if self.issued else None

    @property
    def summary(self) -> str | None:
        """Crossref abstracts arrive as JATS markup."""
        return collapsed(strip_tags(self.abstract, " ")) if self.abstract else None


class Message(Upstream):
    total: int | None = Field(None, alias="total-results")
    items: tuple[Item, ...] = ()


class Found(Upstream):
    """What a search answers."""

    message: Message | None = None


class Registered(Upstream):
    """What a single DOI answers."""

    message: Item | None = None


def record(item: Item) -> Work:
    """One wire record across the boundary."""
    return Work(
        title=collapsed(" ".join(item.title)),
        authors=item.authors,
        year=item.year,
        venue=item.venue,
        doi=item.doi,
        arxiv_id=None,
        openalex_id=None,
        cited_by=item.cited_by,
        abstract=item.summary,
        pdf_url=None,
        landing_url=item.url,
        published=None,
    )


def page(client: httpx.Client, cap: int, extra: Mapping[str, str]) -> Message:
    """One page of works, through the polite pool Crossref still honours."""
    body = json_body(Found, client, WORKS, cap, {**extra, **polite_params()})
    return body.message or Message()


def registration(client: httpx.Client, cap: int, doi: str) -> Item | None:
    """The registrar's record for one DOI, or None where it holds none.

    A DOI Crossref never registered answers 404, which is an answer rather
    than a failure; anything retryable stays a failure.
    """
    try:
        body = json_body(Registered, client, f"{WORKS}/{doi}", cap, polite_params())
    except UpstreamError:
        raise
    except CommandError:
        return None
    return body.message
