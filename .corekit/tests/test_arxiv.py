"""The arXiv feed: which namespace a field lives in, and the pace owed."""

from __future__ import annotations

import httpx
import pytest

from btm_corekit import arxiv

FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>412</opensearch:totalResults>
  <entry>
    <id>https://arxiv.org/abs/2401.01234v2</id>
    <title>A Study of Things</title>
    <summary>We study things.</summary>
    <published>2024-01-05T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <arxiv:journal_ref>J. Things 3</arxiv:journal_ref>
    <arxiv:doi>10.1/xyz</arxiv:doi>
    <link title="pdf" href="https://arxiv.org/pdf/2401.01234v2"/>
  </entry>
</feed>"""

BARE = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'


@pytest.fixture(autouse=True)
def _no_waiting(monkeypatch):
    """The pace is real and tested on its own; every other test skips it."""
    monkeypatch.setattr(arxiv.PACE, "interval", 0.0)


def answering(payload: str) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=payload.encode())
        )
    )


class TestFeed:
    def test_a_feed_parses_into_entries(self):
        feed = arxiv.parse(FEED.encode())
        assert feed.total == 412
        [entry] = feed.entries
        assert entry.title == "A Study of Things"
        assert entry.authors == ("Ada Lovelace", "Grace Hopper")
        assert entry.pdf_url == "https://arxiv.org/pdf/2401.01234v2"

    def test_the_venue_and_doi_come_from_the_arxiv_namespace(self):
        """Both live under `arxiv:`, not Atom. Read as Atom they are silently
        empty, and every paper loses its journal reference."""
        [entry] = arxiv.parse(FEED.encode()).entries
        assert entry.journal_ref == "J. Things 3"
        assert entry.doi == "10.1/xyz"

    def test_an_empty_feed_is_not_a_failure(self):
        assert arxiv.parse(BARE.encode()) == arxiv.Feed()

    def test_a_feed_without_a_total_says_so(self):
        assert arxiv.parse(BARE.encode()).total is None


class TestQuery:
    def test_a_bare_phrase_is_given_a_field(self):
        assert arxiv.fielded("neural scaling") == 'all:"neural scaling"'

    def test_a_fielded_query_is_left_alone(self):
        assert arxiv.fielded('ti:"exact title"') == 'ti:"exact title"'


class TestPace:
    def test_the_first_call_waits_for_nothing(self):
        pace = arxiv.Pace(interval=10.0)
        pace.wait()

    def test_a_second_call_waits_out_the_interval(self, monkeypatch):
        """arXiv's terms ask for one request every three seconds, so the
        sleep belongs to the caller who owes it rather than to advice."""
        slept: list[float] = []
        monkeypatch.setattr("btm_corekit.indexes.arxiv.time.sleep", slept.append)
        pace = arxiv.Pace(interval=3.0)
        pace.wait()
        pace.wait()
        assert slept and 0 < slept[0] <= 3.0


class TestRecord:
    def test_an_entry_crosses_with_what_it_knew(self):
        [entry] = arxiv.parse(FEED.encode()).entries
        work = arxiv.record(entry)
        assert work.title == "A Study of Things"
        assert work.year == 2024
        assert work.published == "2024-01-05"
        assert work.venue == "J. Things 3"
        assert work.doi == "10.1/xyz"
        assert work.arxiv_id == "2401.01234", "the version suffix is not the id"
        assert work.cited_by is None, "arXiv counts no citations"

    def test_a_search_reaches_the_query_endpoint(self):
        feed = arxiv.feed(answering(FEED), 10_000, "things", 1)
        assert feed.total == 412
