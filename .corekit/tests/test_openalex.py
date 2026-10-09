"""OpenAlex: the credential, the spent budget, and what a work still carries."""

from __future__ import annotations

import json

import httpx
import pytest

from btm_corekit import CommandError, UpstreamError, Window, openalex
from btm_corekit.indexes.work import ByArxiv, ByDoi, ByNative


def serving(record: object, status: int = 200) -> httpx.Client:
    payload = json.dumps(record).encode()
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, content=payload)
        )
    )


class TestAccess:
    def test_a_key_rides_as_api_key(self, monkeypatch):
        monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
        assert openalex.access() == openalex.Keyed("k-123")
        assert openalex.params() == {"api_key": "k-123"}

    def test_no_key_is_the_trial_allowance(self, monkeypatch):
        monkeypatch.delenv("BTM_OPENALEX_KEY", raising=False)
        assert isinstance(openalex.access(), openalex.Trial)
        assert openalex.params() == {}

    def test_the_trial_allowance_is_disclosed_once(self, monkeypatch, capsys):
        """A silent allowance stops mid-session with no explanation."""
        monkeypatch.delenv("BTM_OPENALEX_KEY", raising=False)
        openalex._trial_advisory.cache_clear()
        openalex.query()
        openalex.query()
        assert capsys.readouterr().err.count("BTM_OPENALEX_KEY") == 1

    def test_the_contact_does_not_ride_along(self, monkeypatch):
        """OpenAlex retired its mailto pool when it introduced keys."""
        monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
        assert "mailto" not in openalex.query({"search": "x"})


class TestBudget:
    def test_a_spent_allowance_names_the_key_that_lifts_it(self, monkeypatch):
        """409 is how OpenAlex says the day's credits are gone. Read as a
        plain conflict it would exit as the caller's own bad request."""
        monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
        with pytest.raises(UpstreamError, match="BTM_OPENALEX_KEY") as raised:
            openalex.page(serving({}, status=409), 10_000, {})
        assert "credits" in str(raised.value)

    def test_another_refusal_is_left_as_it_was(self, monkeypatch):
        monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
        with pytest.raises(CommandError) as raised:
            openalex.page(serving({}, status=404), 10_000, {})
        assert not isinstance(raised.value, UpstreamError)


class TestWork:
    def test_an_inverted_abstract_rebuilds_its_word_order(self):
        work = openalex.OpenAlexWork.model_validate(
            {"abstract_inverted_index": {"a": [0, 2], "b": [1]}}
        )
        assert work.abstract == "a b a"

    def test_no_abstract_is_absence(self):
        assert openalex.OpenAlexWork().abstract is None

    def test_the_key_is_the_last_segment_of_the_url(self):
        work = openalex.OpenAlexWork(id="https://openalex.org/W123")
        assert work.key == "W123"

    def test_a_work_with_no_venue_still_decodes(self):
        """A work with no registered venue carries a null source, which is
        roughly a third of any page."""
        work = openalex.OpenAlexWork.model_validate(
            {"primary_location": {"source": None}}
        )
        assert work.venue is None

    def test_authors_come_back_flat(self):
        work = openalex.OpenAlexWork.model_validate(
            {"authorships": [{"author": {"display_name": "Ada"}}, {"author": None}]}
        )
        assert work.authors == ("Ada",)

    def test_the_arxiv_id_comes_from_the_registered_doi(self):
        """`ids.arxiv` is gone; the 10.48550 DOI is where it lives now."""
        work = openalex.OpenAlexWork(doi="https://doi.org/10.48550/arXiv.2401.01234")
        assert openalex.record(work).arxiv_id == "2401.01234"

    def test_the_arxiv_id_falls_back_to_the_location(self):
        work = openalex.OpenAlexWork.model_validate(
            {
                "primary_location": {
                    "landing_page_url": "http://arxiv.org/abs/2009.07141"
                }
            }
        )
        assert openalex.record(work).arxiv_id == "2009.07141"

    def test_a_journal_work_claims_no_arxiv_id(self):
        work = openalex.OpenAlexWork(doi="https://doi.org/10.1145/3065386")
        assert openalex.record(work).arxiv_id is None


class TestPage:
    def test_a_page_carries_its_total(self, monkeypatch):
        monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
        page = openalex.page(
            serving({"meta": {"count": 9}, "results": [{"display_name": "T"}]}),
            10_000,
            {},
        )
        assert page.total == 9
        assert openalex.record(page.results[0]).title == "T"


class TestQueryHelpers:
    @pytest.mark.parametrize(
        ("bounds", "expected"),
        [
            ((None, None), ""),
            ((2020, None), "from_publication_date:2020-01-01"),
            ((None, 2024), "to_publication_date:2024-12-31"),
        ],
    )
    def test_a_year_window_names_only_the_bounds_it_has(self, bounds, expected):
        assert openalex.year_filter(*bounds) == expected

    def test_batching_covers_every_id_once(self):
        ids = [str(n) for n in range(7)]
        assert [list(batch) for batch in openalex.batched(ids, 3)] == [
            ["0", "1", "2"],
            ["3", "4", "5"],
            ["6"],
        ]
        assert openalex.batched([], 3) == []


def routed(answer) -> tuple[httpx.Client, list[httpx.Request]]:
    """A client answered per request, keeping every request it saw."""
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        status, body = answer(request)
        return httpx.Response(status, content=json.dumps(body).encode())

    return httpx.Client(transport=httpx.MockTransport(handle)), seen


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
    monkeypatch.setattr(openalex, "BATCH_PAUSE_SECONDS", 0.0)


class TestSearch:
    def test_the_window_rides_as_a_publication_date_filter(self, keyed):
        client, seen = routed(
            lambda request: (200, {"meta": {"count": 9}, "results": [{"id": "W1"}]})
        )
        found = openalex.search(client, 10_000, "q", 5, Window(2020, None))
        assert dict(seen[0].url.params) == {
            "search": "q",
            "per-page": "5",
            "filter": "from_publication_date:2020-01-01",
            "api_key": "k-123",
        }
        assert found.total == 9 and found.works[0].openalex_id == "W1"

    def test_no_window_sends_no_filter(self, keyed):
        client, seen = routed(lambda request: (200, {}))
        assert openalex.search(client, 10_000, "q", 5, Window()).works == ()
        assert "filter" not in seen[0].url.params


class TestLookup:
    @pytest.mark.parametrize(
        ("ref", "segment"),
        [
            (ByNative("W2741809807"), "W2741809807"),
            (ByDoi("10.1145/3065386"), "doi:10.1145/3065386"),
            (ByArxiv("1706.03762"), "doi:10.48550/arxiv.1706.03762"),
        ],
    )
    def test_every_ref_renders_as_a_works_path(self, ref, segment):
        """An arXiv id travels as the DOI arXiv registers, which OpenAlex holds."""
        assert openalex.render(ref) == segment

    def test_a_work_it_does_not_hold_is_absence(self, keyed):
        client, _ = routed(lambda request: (404, {}))
        assert openalex.lookup(client, 10_000, ByDoi("10.9/x")) is None

    def test_a_held_work_crosses(self, keyed):
        client, seen = routed(lambda request: (200, {"id": "W1", "display_name": "T"}))
        work = openalex.lookup(client, 10_000, ByDoi("10.1/a"))
        assert work is not None and work.title == "T"
        assert seen[0].url.path == "/works/doi:10.1/a"


class TestGraph:
    def test_references_walk_the_seed_then_its_ids_in_batches(self, keyed):
        """The walk lifted from lit-review: same requests, same order."""
        cited = [f"https://openalex.org/W{n}" for n in range(60)]

        def answer(request):
            if request.url.path == "/works/W1":
                return 200, {"id": "W1", "referenced_works": cited}
            ids = request.url.params["filter"].removeprefix("openalex_id:")
            return 200, {"results": [{"id": key} for key in ids.split("|")]}

        client, seen = routed(answer)
        found = openalex.references(client, 10_000, ByNative("W1"), 55)
        assert found.total == 60, "every reference the seed lists"
        assert len(found.works) == 55
        paths = [request.url.path for request in seen]
        assert paths == ["/works/W1", "/works", "/works"]
        assert seen[1].url.params["per-page"] == "50"
        assert seen[2].url.params["filter"].count("|") == 4

    def test_references_of_a_work_it_does_not_hold_refuse(self, keyed):
        client, _ = routed(lambda request: (404, {}))
        with pytest.raises(CommandError, match="holds no work"):
            openalex.references(client, 10_000, ByDoi("10.9/x"), 5)

    def test_citations_of_a_native_seed_are_one_request(self, keyed):
        client, seen = routed(lambda request: (200, {"meta": {"count": 3}}))
        found = openalex.citations(client, 10_000, ByNative("W1"), 7)
        assert found.total == 3
        assert len(seen) == 1
        assert seen[0].url.params["filter"] == "cites:W1"
        assert seen[0].url.params["per-page"] == "7"

    def test_citations_of_a_doi_seed_resolve_its_id_first(self, keyed):
        def answer(request):
            if request.url.path.startswith("/works/doi:"):
                return 200, {"id": "https://openalex.org/W9"}
            return 200, {"meta": {"count": 0}}

        client, seen = routed(answer)
        openalex.citations(client, 10_000, ByDoi("10.1/a"), 7)
        assert seen[1].url.params["filter"] == "cites:W9"
