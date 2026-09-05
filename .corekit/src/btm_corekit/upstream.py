"""The scholarly indexes, as records rather than raw JSON.

One decoder per index, shared by every member that searches them. A record
here is the index's own shape; projecting it into a member's domain type is
the member's business. Another service owns these shapes and may add a
field at any time, so extras are ignored and every field has a default.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from typing import Any

import httpx
from pydantic import ConfigDict, Field, model_validator

from btm_corekit.errors import CommandError, UpstreamError
from btm_corekit.http import get_bytes, openalex_query
from btm_corekit.models import Model
from btm_corekit.origin import polite_params

OPENALEX_WORKS = "https://api.openalex.org/works"
CROSSREF_WORKS = "https://api.crossref.org/works"
ARXIV_QUERY = "https://export.arxiv.org/api/query"

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"


class Upstream(Model):
    """A record another service owns and may extend at any time."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _null_is_absent(cls, raw: Any) -> Any:
        """An index spells a field it holds nothing for as an explicit null:
        OpenAlex nulls `primary_location.source` for a work with no venue. A
        default covers an absent key, so drop the null and let it stand."""
        if not isinstance(raw, Mapping):
            return raw
        return {key: value for key, value in raw.items() if value is not None}


def _json(
    client: httpx.Client, url: str, cap: int, params: Mapping[str, str]
) -> object:
    payload = get_bytes(client, url, cap, params)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as err:
        raise UpstreamError(f"non-JSON response from {url}") from err


# --- OpenAlex ---


class Named(Upstream):
    display_name: str = ""


class Authorship(Upstream):
    author: Named = Named()


class Location(Upstream):
    source: Named = Named()


class OpenAccess(Upstream):
    oa_url: str | None = None


class ExternalIds(Upstream):
    arxiv: str = ""


class OpenAlexWork(Upstream):
    id: str = ""
    display_name: str = ""
    doi: str | None = None
    ids: ExternalIds = ExternalIds()
    publication_year: int | None = None
    cited_by_count: int | None = None
    authorships: tuple[Authorship, ...] = ()
    primary_location: Location = Location()
    open_access: OpenAccess = OpenAccess()
    abstract_inverted_index: dict[str, tuple[int, ...]] | None = None
    referenced_works: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        """The bare work id, which is the last segment of its URL."""
        return self.id.rsplit("/", 1)[-1]

    @property
    def abstract(self) -> str:
        """OpenAlex stores an abstract as a word-to-positions index."""
        if not self.abstract_inverted_index:
            return ""
        places = sorted(
            (position, word)
            for word, spots in self.abstract_inverted_index.items()
            for position in spots
        )
        return " ".join(word for _, word in places)

    @property
    def authors(self) -> tuple[str, ...]:
        return tuple(
            entry.author.display_name
            for entry in self.authorships
            if entry.author.display_name
        )


class OpenAlexMeta(Upstream):
    count: int = 0


class OpenAlexPage(Upstream):
    meta: OpenAlexMeta = OpenAlexMeta()
    results: tuple[OpenAlexWork, ...] = ()


def openalex_page(
    client: httpx.Client, cap: int, params: Mapping[str, str]
) -> OpenAlexPage:
    """One page of works. The caller builds the query; the credential rides
    along here so no caller can forget it."""
    body = _json(client, OPENALEX_WORKS, cap, openalex_query(params))
    return OpenAlexPage.model_validate(body)


def openalex_work(client: httpx.Client, cap: int, ref: str) -> OpenAlexWork:
    """One work by its id or `doi:<doi>` form."""
    body = _json(client, f"{OPENALEX_WORKS}/{ref}", cap, openalex_query())
    return OpenAlexWork.model_validate(body)


def year_filter(from_year: int | None, to_year: int | None) -> str:
    parts = []
    if from_year:
        parts.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        parts.append(f"to_publication_date:{to_year}-12-31")
    return ",".join(parts)


# --- Crossref ---


class CrossrefAuthor(Upstream):
    given: str = ""
    family: str = ""

    @property
    def name(self) -> str:
        return f"{self.given} {self.family}".strip()


class CrossrefIssued(Upstream):
    date_parts: tuple[tuple[int | None, ...], ...] = Field((), alias="date-parts")

    @property
    def year(self) -> int | None:
        return self.date_parts[0][0] if self.date_parts and self.date_parts[0] else None


class CrossrefItem(Upstream):
    title: tuple[str, ...] = ()
    container_title: tuple[str, ...] = Field((), alias="container-title")
    author: tuple[CrossrefAuthor, ...] = ()
    doi: str | None = Field(None, alias="DOI")
    url: str = Field("", alias="URL")
    abstract: str = ""
    issued: CrossrefIssued = CrossrefIssued()
    cited_by: int | None = Field(None, alias="is-referenced-by-count")

    @property
    def authors(self) -> tuple[str, ...]:
        return tuple(person.name for person in self.author if person.name)


class CrossrefMessage(Upstream):
    total: int = Field(0, alias="total-results")
    items: tuple[CrossrefItem, ...] = ()


class CrossrefResponse(Upstream):
    message: CrossrefMessage = CrossrefMessage()


def crossref_page(
    client: httpx.Client, cap: int, params: Mapping[str, str]
) -> CrossrefMessage:
    """One page of works. `mailto` reaches the polite pool, which Crossref
    still honours."""
    body = _json(client, CROSSREF_WORKS, cap, {**params, **polite_params()})
    return CrossrefResponse.model_validate(body).message


def crossref_work(client: httpx.Client, cap: int, doi: str) -> CrossrefItem | None:
    """The registrar's record for one DOI, or None where it holds none."""
    try:
        body = _json(client, f"{CROSSREF_WORKS}/{doi}", cap, polite_params())
    except UpstreamError:
        raise
    except CommandError:
        return None
    payload = body.get("message") if isinstance(body, dict) else None
    return CrossrefItem.model_validate(payload) if payload else None


def crossref_filter(from_year: int | None, to_year: int | None) -> str:
    parts = []
    if from_year:
        parts.append(f"from-pub-date:{from_year}-01-01")
    if to_year:
        parts.append(f"until-pub-date:{to_year}-12-31")
    return ",".join(parts)


# --- arXiv ---


class ArxivEntry(Upstream):
    id: str = ""
    title: str = ""
    summary: str = ""
    published: str = ""
    journal_ref: str = ""
    doi: str | None = None
    authors: tuple[str, ...] = ()
    pdf_url: str | None = None


class ArxivFeed(Upstream):
    total: int = 0
    entries: tuple[ArxivEntry, ...] = ()


def _entry(node: ET.Element) -> ArxivEntry:
    def text(tag: str) -> str:
        return (node.findtext(ATOM + tag) or "").strip()

    pdf = next(
        (
            link.get("href")
            for link in node.findall(ATOM + "link")
            if link.get("title") == "pdf"
        ),
        None,
    )
    return ArxivEntry(
        id=text("id"),
        title=text("title"),
        summary=text("summary"),
        published=text("published"),
        journal_ref=text("journal_ref"),
        doi=node.findtext(ARXIV_NS + "doi"),
        authors=tuple(
            (person.text or "").strip()
            for person in node.findall(f"{ATOM}author/{ATOM}name")
            if (person.text or "").strip()
        ),
        pdf_url=pdf,
    )


def arxiv_feed(client: httpx.Client, cap: int, query: str, limit: int) -> ArxivFeed:
    """arXiv ranks a fielded query far better than a bare phrase, so a query
    without a field marker is wrapped in one."""
    fielded = query if ":" in query else f'all:"{query}"'
    payload = get_bytes(
        client,
        ARXIV_QUERY,
        cap,
        {"search_query": fielded, "max_results": str(limit)},
    )
    root = ET.fromstring(payload)
    total = root.findtext(OPENSEARCH + "totalResults") or "0"
    return ArxivFeed(
        total=int(total) if total.strip().isdigit() else 0,
        entries=tuple(_entry(node) for node in root.findall(ATOM + "entry")),
    )


def batched(items: Sequence[str], size: int) -> list[Sequence[str]]:
    """Slices of at most `size`, for an index that takes ids in bulk."""
    return [items[start : start + size] for start in range(0, len(items), size)]
