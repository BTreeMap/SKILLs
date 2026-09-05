"""Whether the real indexes still answer the way these decoders parse them.

A mock proves our half of the contract: given this body, the decoder yields
this record. It cannot prove the service still sends that body, and that is
the half that breaks without anyone editing this repository. So these ask
the services themselves, and assert on the fields the crossings depend on
rather than on a bare 200: a page of works whose every title is empty
parses perfectly and is still a broken decoder.

Advisory by construction. A third party rate-limiting or having an outage
is not this repository breaking, so the gate runs these without letting
them redden it.
"""

from __future__ import annotations

import httpx
import pytest

from btm_corekit import arxiv, build_client, crossref, doi, openalex

pytestmark = pytest.mark.network

CAP = 16 * 1024 * 1024

ALEXNET_DOI = "10.1145/3065386"
ALEXNET_TITLE = "imagenet classification"
UNREGISTERED_DOI = "10.9999/definitely-not-a-registered-doi"

ARXIV_SOURCE = "S4306400194"
"""OpenAlex's id for arXiv, so a page of arXiv-hosted works comes back."""

PAGE = 25


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    """A longer read than the members use: these assert on shape, and a slow
    afternoon upstream should not read as a shape that changed."""
    with build_client("corekit-live", read_timeout=90.0) as made:
        yield made


class TestOpenAlex:
    def test_a_search_answers_with_works(self, client):
        page = openalex.page(
            client,
            CAP,
            {"search": "convolutional neural network", "per-page": str(PAGE)},
        )
        assert page.total and page.total > 0, "the meta count is what paging reads"
        assert len(page.results) == PAGE

    def test_the_fields_a_crossing_depends_on_are_populated(self, client):
        page = openalex.page(
            client,
            CAP,
            {"search": "convolutional neural network", "per-page": str(PAGE)},
        )
        works = [openalex.record(found) for found in page.results]
        assert all(work.title for work in works), "every work is titled"
        assert sum(work.year is not None for work in works) > PAGE // 2
        assert sum(work.cited_by is not None for work in works) > PAGE // 2
        assert any(work.authors for work in works)
        assert any(work.venue for work in works), "some work is published somewhere"
        assert any(work.abstract for work in works), "the inverted index still rebuilds"

    def test_a_work_with_no_venue_is_ordinary_rather_than_fatal(self, client):
        """Roughly a third of any page nulls `primary_location.source`. This
        is the shape that a nested default alone does not survive."""
        page = openalex.page(
            client,
            CAP,
            {"search": "convolutional neural network", "per-page": str(PAGE)},
        )
        assert any(
            found.primary_location and found.primary_location.source is None
            for found in page.results
        ), "no null venue on this page; the tolerance is untested by it"

    def test_an_arxiv_hosted_work_still_yields_its_arxiv_id(self, client):
        """`ids.arxiv` is gone from the API. If neither the registered DOI nor
        the location URL carried the id, arXiv records would stop deduplicating
        against their preprints and nothing else would say so."""
        page = openalex.page(
            client,
            CAP,
            {
                "filter": f"primary_location.source.id:{ARXIV_SOURCE}",
                "per-page": str(PAGE),
            },
        )
        found = [openalex.record(work).arxiv_id for work in page.results]
        assert sum(one is not None for one in found) > PAGE // 2

    def test_one_work_by_id_carries_its_references(self, client):
        work = openalex.work(client, CAP, f"doi:{ALEXNET_DOI}")
        assert work.key and work.key.startswith("W")
        assert work.referenced_works, "backward snowball reads exactly this"


class TestCrossref:
    def test_a_search_answers_with_items(self, client):
        message = crossref.page(
            client, CAP, {"query": "convolutional neural network", "rows": "10"}
        )
        assert message.total and message.total > 0
        assert len(message.items) == 10
        assert all(crossref.record(item).title for item in message.items)

    def test_a_registered_doi_answers_with_its_own_record(self, client):
        item = crossref.registration(client, CAP, ALEXNET_DOI)
        assert item is not None, "the single-DOI body puts the item under message"
        work = crossref.record(item)
        assert work.title and ALEXNET_TITLE in work.title.lower()
        assert work.year == 2017

    def test_an_unregistered_doi_answers_with_nothing(self, client):
        assert crossref.registration(client, CAP, UNREGISTERED_DOI) is None


class TestArxiv:
    """One feed, several questions. arXiv asks for one request every three
    seconds, so the class fetches once rather than once per assertion."""

    @pytest.fixture(scope="class")
    def feed(self, client) -> arxiv.Feed:
        return arxiv.feed(client, CAP, "all:superconductivity", PAGE)

    def test_a_search_answers_with_entries(self, feed):
        assert feed.total and feed.total > 0
        assert len(feed.entries) == PAGE

    def test_the_fields_a_crossing_depends_on_are_populated(self, feed):
        works = [arxiv.record(entry) for entry in feed.entries]
        assert all(work.title for work in works)
        assert all(work.abstract for work in works)
        assert all(work.authors for work in works)
        assert all(work.arxiv_id for work in works), "the id parses out of every id URL"
        assert all(work.pdf_url for work in works)
        assert all(work.published for work in works)

    def test_the_venue_and_doi_survive_their_namespace(self, feed):
        """Both live under `arxiv:` rather than Atom. Read from the wrong
        namespace they come back empty on every entry and nothing errors, so
        only a real feed catches it."""
        assert any(entry.journal_ref for entry in feed.entries)
        assert any(entry.doi for entry in feed.entries)


class TestDoi:
    def test_a_live_handle_redirects(self, client):
        assert doi.resolves(client, ALEXNET_DOI) == doi.RESOLVED

    def test_an_unknown_handle_does_not(self, client):
        assert doi.resolves(client, UNREGISTERED_DOI) == 404
