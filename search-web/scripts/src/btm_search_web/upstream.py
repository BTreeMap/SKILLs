"""What each service returns, as records this skill can read.

Another service owns these shapes and may add a field at any time, so extras
are ignored and every field has a default. What they buy is that a
projection reads a typed record rather than a chain of `.get` calls.
"""

from __future__ import annotations

from pydantic import Field

from btm_corekit import Upstream


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
