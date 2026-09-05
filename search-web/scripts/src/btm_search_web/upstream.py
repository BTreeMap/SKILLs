"""What each service returns, as records this skill can read.

These sit on the kernel's tolerance boundary: an unknown key is ignored, a
null reads as absence, and no field carries a stand-in default. What they
buy is that a projection reads a typed record rather than a chain of `.get`
calls.
"""

from __future__ import annotations

from pydantic import Field

from btm_corekit import Upstream


class RelatedTopic(Upstream):
    """One neighbouring term. A grouping entry carries `Name` and `Topics`
    instead of these two, and so decodes to a topic with no text."""

    text: str | None = Field(None, alias="Text")
    url: str | None = Field(None, alias="FirstURL")


class InstantAnswer(Upstream):
    """A definition or an abstract, never a ranked list."""

    heading: str | None = Field(None, alias="Heading")
    abstract: str | None = Field(None, alias="AbstractText")
    abstract_url: str | None = Field(None, alias="AbstractURL")
    answer: str | None = Field(None, alias="Answer")
    definition: str | None = Field(None, alias="Definition")
    definition_url: str | None = Field(None, alias="DefinitionURL")
    topics: tuple[RelatedTopic, ...] = Field((), alias="RelatedTopics")

    @property
    def says(self) -> str | None:
        """What the service actually answered with. A term query is often a
        definition where a subject query is an abstract, and either may be
        the only one populated."""
        return self.abstract or self.answer or self.definition

    @property
    def source_url(self) -> str:
        """The page the answer came from, matched to whichever it was."""
        if self.abstract:
            return self.abstract_url or ""
        if self.definition and not self.answer:
            return self.definition_url or self.abstract_url or ""
        return self.abstract_url or ""


class WikiPage(Upstream):
    key: str | None = None
    title: str | None = None
    description: str | None = None


class WikiSearch(Upstream):
    pages: tuple[WikiPage, ...] = ()


class WikiUrls(Upstream):
    page: str | None = None


class WikiContentUrls(Upstream):
    desktop: WikiUrls | None = None


class WikiSummary(Upstream):
    extract: str | None = None
    content_urls: WikiContentUrls | None = None

    @property
    def url(self) -> str | None:
        desktop = self.content_urls.desktop if self.content_urls else None
        return desktop.page if desktop else None
