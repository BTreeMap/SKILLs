"""OpenAlex: a keyed index of works across every field.

Since 2026-02-13 a call spends credits against a key, and a keyless call
draws on a small daily allowance before the service answers 409. The
allowance is worth roughly ten searches, so an agent meets that wall inside
one session; the refusal names the fix rather than the status.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache

import httpx

from btm_corekit.indexes.work import Work, collapsed
from btm_corekit.net.http import HTTP_CONFLICT
from btm_corekit.net.wire import Upstream, json_body
from btm_corekit.report.channels import signal
from btm_corekit.report.errors import CommandError, UpstreamError

WORKS = "https://api.openalex.org/works"

KEY_ENV = "BTM_OPENALEX_KEY"

ID_BATCH_SIZE = 50
"""Ids per `openalex_id:a|b|c` filter, which the service caps at 50."""


@dataclass(frozen=True, slots=True)
class Keyed:
    key: str


@dataclass(frozen=True, slots=True)
class Trial:
    """No key: a small daily allowance, then 409."""


Access = Keyed | Trial


def access() -> Access:
    key = os.environ.get(KEY_ENV)
    return Keyed(key) if key else Trial()


def params() -> dict[str, str]:
    """The credential, or nothing. Pure: no advisory, no request."""
    match access():
        case Keyed(key):
            return {"api_key": key}
        case Trial():
            return {}


@cache
def _trial_advisory() -> None:
    """Once per process; the cache is the guard."""
    signal(
        "no OpenAlex key: a keyless call draws on a small daily allowance, "
        f"then 409s. Set {KEY_ENV} to a free key from openalex.org/settings/api"
    )


def query(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Query parameters for one call, credential included. Discloses a keyless
    run at the first call, since it otherwise stops partway through a session.

    OpenAlex retired its `mailto` polite pool when it introduced keys, so the
    contact that marks a Crossref request has no place here.
    """
    keyed = params()
    if not keyed:
        _trial_advisory()
    return {**(extra or {}), **keyed}


def batched(items: Sequence[str], size: int = ID_BATCH_SIZE) -> list[Sequence[str]]:
    """Slices of at most `size`, for the filter that takes ids in bulk."""
    return [items[start : start + size] for start in range(0, len(items), size)]


def year_filter(from_year: int | None, to_year: int | None) -> str:
    parts = []
    if from_year:
        parts.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        parts.append(f"to_publication_date:{to_year}-12-31")
    return ",".join(parts)


class Named(Upstream):
    display_name: str | None = None


class Authorship(Upstream):
    author: Named | None = None


class Location(Upstream):
    source: Named | None = None
    landing_page_url: str | None = None
    pdf_url: str | None = None


class OpenAccess(Upstream):
    oa_url: str | None = None


class OpenAlexWork(Upstream):
    """One work. A collection defaults to empty because a consumer here reads
    an absent list and an empty one the same way; every other field says its
    own absence."""

    id: str | None = None
    display_name: str | None = None
    doi: str | None = None
    publication_year: int | None = None
    cited_by_count: int | None = None
    authorships: tuple[Authorship, ...] = ()
    primary_location: Location | None = None
    open_access: OpenAccess | None = None
    abstract_inverted_index: dict[str, tuple[int, ...]] | None = None
    referenced_works: tuple[str, ...] = ()

    @property
    def key(self) -> str | None:
        """The bare work id, which is the last segment of its URL."""
        return self.id.rsplit("/", 1)[-1] if self.id else None

    @property
    def abstract(self) -> str | None:
        """OpenAlex stores an abstract as a word-to-positions index."""
        if not self.abstract_inverted_index:
            return None
        places = sorted(
            (position, word)
            for word, spots in self.abstract_inverted_index.items()
            for position in spots
        )
        return " ".join(word for _, word in places) or None

    @property
    def authors(self) -> tuple[str, ...]:
        named = (
            entry.author.display_name for entry in self.authorships if entry.author
        )
        return tuple(name for name in map(collapsed, named) if name)

    @property
    def venue(self) -> str | None:
        source = self.primary_location.source if self.primary_location else None
        return collapsed(source.display_name) if source else None

    @property
    def landing_url(self) -> str | None:
        """Where the work is read. The DOI is the durable address; the
        location's own page is what an index-only record has."""
        page = self.primary_location.landing_page_url if self.primary_location else None
        return self.doi or page or self.id

    @property
    def pdf_url(self) -> str | None:
        location = self.primary_location.pdf_url if self.primary_location else None
        return (self.open_access.oa_url if self.open_access else None) or location

    @property
    def arxiv_ref(self) -> str | None:
        """OpenAlex stopped carrying `ids.arxiv`. What remains is the
        registered `10.48550/arXiv.NNNN.NNNNN` DOI, and, for a work whose
        primary location is arXiv, the abs URL. Either parses."""
        page = self.primary_location.landing_page_url if self.primary_location else None
        return self.doi or page


class Meta(Upstream):
    count: int | None = None


class Page(Upstream):
    meta: Meta | None = None
    results: tuple[OpenAlexWork, ...] = ()

    @property
    def total(self) -> int | None:
        return self.meta.count if self.meta else None


def record(work: OpenAlexWork) -> Work:
    """One wire record across the boundary."""
    return Work(
        title=collapsed(work.display_name),
        authors=work.authors,
        year=work.publication_year,
        venue=work.venue,
        doi=work.doi,
        arxiv_id=work.arxiv_ref,
        openalex_id=work.key,
        cited_by=work.cited_by_count,
        abstract=collapsed(work.abstract),
        pdf_url=work.pdf_url,
        landing_url=work.landing_url,
        published=None,
    )


@contextmanager
def _budget() -> Iterator[None]:
    """409 is how OpenAlex says the day's allowance is gone. Read generically
    a conflict is the request's own fault and no retry helps; here it is a
    budget, and the fix is a key rather than a different request."""
    try:
        yield
    except CommandError as err:
        if err.status != HTTP_CONFLICT:
            raise
        raise UpstreamError(
            f"OpenAlex credits are spent for today: set {KEY_ENV} to a free "
            "key from openalex.org/settings/api, or wait for the reset"
        ) from err


def page(client: httpx.Client, cap: int, extra: Mapping[str, str]) -> Page:
    """One page of works. The caller builds the query; the credential rides
    along here so no caller can forget it."""
    with _budget():
        return json_body(Page, client, WORKS, cap, query(extra))


def work(client: httpx.Client, cap: int, ref: str) -> OpenAlexWork:
    """One work by its id or `doi:<doi>` form."""
    with _budget():
        return json_body(OpenAlexWork, client, f"{WORKS}/{ref}", cap, query())
