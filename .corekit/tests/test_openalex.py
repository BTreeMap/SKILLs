"""OpenAlex: the credential, the spent budget, and what a work still carries."""

from __future__ import annotations

import json

import httpx
import pytest

from btm_corekit import CommandError, UpstreamError, openalex


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
