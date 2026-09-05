"""The domain record's smart constructors: what each field will accept."""

from __future__ import annotations

import pytest

from btm_corekit import Work, collapsed, normalize_arxiv_id, normalize_doi

BARE: dict[str, object] = {
    "title": None,
    "authors": (),
    "year": None,
    "venue": None,
    "doi": None,
    "arxiv_id": None,
    "openalex_id": None,
    "cited_by": None,
    "abstract": None,
    "pdf_url": None,
    "landing_url": None,
    "published": None,
}


def work(**overrides: object) -> Work:
    return Work(**{**BARE, **overrides})


class TestCollapsed:
    def test_runs_of_whitespace_collapse(self):
        assert collapsed("Hello   world\n") == "Hello world"

    def test_nothing_left_is_absence(self):
        assert collapsed("   ") is None
        assert collapsed(None) is None


class TestDoi:
    @pytest.mark.parametrize(
        "raw", ["10.1/AbC", "https://doi.org/10.1/AbC", "DOI:10.1/AbC"]
    )
    def test_the_written_forms_converge(self, raw):
        assert normalize_doi(raw) == "10.1/abc"

    def test_a_non_doi_is_absence_rather_than_a_rejection(self):
        assert normalize_doi("not-a-doi") is None
        assert work(doi="not-a-doi").doi is None


class TestArxivId:
    @pytest.mark.parametrize(
        "raw",
        [
            "2401.01234",
            "arXiv:2401.01234v3",
            "https://arxiv.org/abs/2401.01234",
            "http://arxiv.org/abs/2401.01234v2",
            "10.48550/arXiv.2401.01234",
        ],
    )
    def test_every_written_form_converges(self, raw):
        """The last two matter most: OpenAlex stopped sending `ids.arxiv`, so
        the registered DOI and the location URL are all that is left."""
        assert normalize_arxiv_id(raw) == "2401.01234"

    def test_the_four_digit_numbering_still_parses(self):
        assert normalize_arxiv_id("https://arxiv.org/abs/0704.0001") == "0704.0001"

    def test_something_else_entirely_is_absence(self):
        assert normalize_arxiv_id("https://example.org/paper") is None


class TestPlausibility:
    @pytest.mark.parametrize("raw", [0, -5, 99999, True])
    def test_an_impossible_year_is_absence(self, raw):
        assert work(year=raw).year is None

    def test_a_real_year_survives(self):
        assert work(year=2024).year == 2024

    @pytest.mark.parametrize("raw", [-1, True])
    def test_an_impossible_count_is_absence(self, raw):
        assert work(cited_by=raw).cited_by is None

    def test_a_count_of_zero_is_a_count(self):
        assert work(cited_by=0).cited_by == 0

    def test_a_timestamp_keeps_only_its_day(self):
        assert work(published="2024-01-05T00:00:00Z").published == "2024-01-05"

    def test_a_non_date_is_absence(self):
        assert work(published="sometime").published is None


class TestTitle:
    def test_an_untitled_record_still_shows_something(self):
        assert work().names == "(untitled)"

    def test_a_title_is_its_own_name(self):
        assert work(title="T").names == "T"
