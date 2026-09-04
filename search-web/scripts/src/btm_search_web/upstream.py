"""What each service returns, as records this skill can read.

Another service owns these shapes and may add a field at any time, so extras
are ignored and every field has a default. What they buy is that a
projection reads a typed record rather than a chain of `.get` calls.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from btm_corekit import Model


class Upstream(Model):
    model_config = ConfigDict(frozen=True, extra="ignore")


class RelatedTopic(Upstream):
    text: str = Field("", alias="Text")
    url: str = Field("", alias="FirstURL")


class InstantAnswer(Upstream):
    heading: str = Field("", alias="Heading")
    abstract: str = Field("", alias="AbstractText")
    abstract_url: str = Field("", alias="AbstractURL")
    answer: str = Field("", alias="Answer")
    topics: tuple[RelatedTopic, ...] = Field((), alias="RelatedTopics")


class WikiPage(Upstream):
    key: str = ""
    title: str = ""
    description: str | None = None


class WikiSearch(Upstream):
    pages: tuple[WikiPage, ...] = ()


class WikiUrls(Upstream):
    page: str = ""


class WikiContentUrls(Upstream):
    desktop: WikiUrls = WikiUrls()


class WikiSummary(Upstream):
    extract: str = ""
    content_urls: WikiContentUrls = WikiContentUrls()


class OpenAlexWork(Upstream):
    id: str = ""
    display_name: str = ""
    doi: str | None = None
    publication_year: int | None = None
    cited_by_count: int | None = None
    abstract_inverted_index: dict[str, tuple[int, ...]] | None = None


class OpenAlexPage(Upstream):
    results: tuple[OpenAlexWork, ...] = ()


class CrossrefIssued(Upstream):
    date_parts: tuple[tuple[int | None, ...], ...] = Field((), alias="date-parts")

    @property
    def year(self) -> int | None:
        return self.date_parts[0][0] if self.date_parts and self.date_parts[0] else None


class CrossrefItem(Upstream):
    title: tuple[str, ...] = ()
    doi: str | None = Field(None, alias="DOI")
    url: str = Field("", alias="URL")
    abstract: str = ""
    issued: CrossrefIssued = CrossrefIssued()
    cited_by: int | None = Field(None, alias="is-referenced-by-count")


class CrossrefMessage(Upstream):
    items: tuple[CrossrefItem, ...] = ()


class CrossrefResponse(Upstream):
    message: CrossrefMessage = CrossrefMessage()
