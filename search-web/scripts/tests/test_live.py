"""Whether the services this skill reads still answer as it parses them.

Advisory: these ask real endpoints, and being throttled is not this
repository breaking. They assert on the fields a result is built from, since
a body that decodes to empty strings parses perfectly and is still useless.
"""

from __future__ import annotations

import pytest
from btm_search_web import sources
from btm_search_web.constants import Scholar

pytestmark = pytest.mark.network

WIKI_SUBJECT = "Lorenz system"
DEFINED_TERM = "monoid"


class TestWiki:
    """Wikipedia blocks a caller whose agent names no contact and meters an
    anonymous one far tighter, so a passing run also says the origin header
    is still acceptable."""

    def test_a_search_answers_with_summarized_pages(self):
        found = sources.wiki(WIKI_SUBJECT, 3)
        assert len(found) == 3
        assert all(row.title for row in found)
        assert all(row.url.startswith("https://en.wikipedia.org/") for row in found)
        assert any(row.snippet for row in found), "the summary endpoint still answers"


class TestInstant:
    def test_a_term_comes_back_defined_or_abstracted(self):
        """The service answers a term with a definition and a subject with an
        abstract, and populates only the one it chose."""
        found = sources.instant(DEFINED_TERM)
        assert found, "no instant answer at all"
        assert any(row.snippet for row in found)


class TestWeb:
    def test_a_query_ranks_something(self):
        """The one backend with no official API. An empty list is throttling
        as often as absence, so this is the flakiest check here."""
        found = sources.web("chaos theory", 3)
        assert found, "no web backend answered"
        assert all(row.url.startswith("http") for row in found)


class TestScholar:
    @pytest.mark.parametrize("source", list(Scholar))
    def test_every_index_answers_in_the_one_result_shape(self, source):
        found = sources.scholar("convolutional neural network", 5, source)
        assert found
        assert all(row.title for row in found)
        assert all(row.source == source.value for row in found)
        assert any(row.year for row in found), "a scholarly row carries its year"


class TestFetch:
    def test_an_article_comes_back_as_readable_text(self):
        text = sources.fetch("https://en.wikipedia.org/wiki/Monoid")
        assert "associative" in text.lower()
        assert "<div" not in text, "markup is stripped rather than passed through"
