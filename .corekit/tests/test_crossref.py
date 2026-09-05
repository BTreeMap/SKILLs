"""Crossref: two shapes under one key, and the dates it does not know."""

from __future__ import annotations

import json

import httpx
import pytest

from btm_corekit import UpstreamError, crossref


def serving(record: object, status: int = 200) -> httpx.Client:
    payload = json.dumps(record).encode()
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, content=payload)
        )
    )


class TestItem:
    def test_a_date_part_becomes_a_year(self):
        item = crossref.Item.model_validate({"issued": {"date-parts": [[2022, 4]]}})
        assert item.year == 2022

    def test_a_date_crossref_does_not_know_is_absence(self):
        """It writes an unknown date as `[[null]]`: the outer list is there
        and the year inside it is not, which is most of a search page."""
        item = crossref.Item.model_validate({"issued": {"date-parts": [[None]]}})
        assert item.year is None

    def test_no_issued_block_at_all_is_absence(self):
        assert crossref.Item().year is None

    def test_a_name_joins_its_halves(self):
        item = crossref.Item.model_validate(
            {"author": [{"given": "Grace", "family": "Hopper"}, {"family": "Ada"}]}
        )
        assert item.authors == ("Grace Hopper", "Ada")

    def test_an_author_with_neither_half_is_dropped(self):
        item = crossref.Item.model_validate({"author": [{"sequence": "first"}]})
        assert item.authors == ()

    def test_a_jats_abstract_comes_back_as_text(self):
        item = crossref.Item.model_validate(
            {"abstract": "<jats:p>We show that</jats:p>"}
        )
        assert item.summary == "We show that"

    def test_the_aliased_fields_read(self):
        item = crossref.Item.model_validate(
            {
                "DOI": "10.1/a",
                "URL": "https://doi.org/10.1/a",
                "container-title": ["J. Things"],
                "is-referenced-by-count": 12,
            }
        )
        assert item.doi == "10.1/a"
        assert item.venue == "J. Things"
        assert item.cited_by == 12
        assert item.url == "https://doi.org/10.1/a"


class TestSearch:
    def test_a_page_carries_its_total(self):
        message = crossref.page(
            serving({"message": {"total-results": 4, "items": [{"DOI": "10.1/a"}]}}),
            10_000,
            {},
        )
        assert message.total == 4
        assert crossref.record(message.items[0]).doi == "10.1/a"

    def test_an_empty_answer_is_an_empty_page(self):
        assert crossref.page(serving({}), 10_000, {}).items == ()


class TestRegistration:
    def test_one_doi_answers_with_the_item_itself(self):
        """A search puts a list under `message`; a single DOI puts the record
        there. Reading one as the other loses every field."""
        item = crossref.registration(
            serving({"message": {"DOI": "10.1/a", "title": ["T"]}}), 10_000, "10.1/a"
        )
        assert item is not None
        assert item.doi == "10.1/a"
        assert crossref.record(item).title == "T"

    def test_an_unregistered_doi_is_an_answer_not_a_failure(self):
        assert crossref.registration(serving({}, status=404), 10_000, "10.9/x") is None

    def test_a_service_failure_stays_a_failure(self):
        with pytest.raises(UpstreamError):
            crossref.registration(serving({}, status=503), 10_000, "10.1/a")


class TestQueryHelpers:
    def test_crossref_spells_its_window_its_own_way(self):
        assert crossref.date_filter(2020, 2024) == (
            "from-pub-date:2020-01-01,until-pub-date:2024-12-31"
        )

    def test_no_bounds_is_no_filter(self):
        assert crossref.date_filter(None, None) == ""
