"""Projection: one index record becomes one Paper."""

from __future__ import annotations

from btm_corekit import ArxivEntry, CrossrefItem, OpenAlexWork
from btm_lit_review.upstream import (
    paper_from_arxiv,
    paper_from_crossref,
    paper_from_openalex,
)


def openalex(**fields) -> OpenAlexWork:
    return OpenAlexWork.model_validate(fields)


class TestOpenAlex:
    def test_a_work_becomes_a_paper_with_its_identifiers(self):
        paper = paper_from_openalex(
            openalex(
                display_name="A Study",
                doi="https://doi.org/10.1/abc",
                publication_year=2023,
                cited_by_count=7,
                authorships=[{"author": {"display_name": "Ada"}}],
            )
        )
        assert paper.title == "A Study"
        assert paper.doi == "10.1/abc"
        assert paper.year == 2023
        assert paper.authors == ("Ada",)

    def test_an_inverted_abstract_rebuilds_its_word_order(self):
        work = openalex(
            display_name="T", abstract_inverted_index={"a": [0, 2], "b": [1]}
        )
        assert paper_from_openalex(work).abstract == "a b a"

    def test_a_sparse_work_still_parses(self):
        assert paper_from_openalex(openalex(display_name="Bare")).title == "Bare"

    def test_a_work_without_a_name_is_marked_untitled(self):
        """The corpus never holds a blank title; absence is stated instead."""
        assert paper_from_openalex(openalex()).title == "(untitled)"


class TestArxiv:
    def test_an_entry_becomes_a_paper(self):
        paper = paper_from_arxiv(
            ArxivEntry(
                id="http://arxiv.org/abs/2401.01234v2",
                title="A Study of Things",
                summary="We study things.",
                published="2024-01-05T00:00:00Z",
                doi="10.1/xyz",
                authors=("Ada Lovelace",),
            )
        )
        assert paper.title == "A Study of Things"
        assert paper.arxiv_id == "2401.01234"
        assert paper.doi == "10.1/xyz"
        assert paper.authors == ("Ada Lovelace",)
        assert paper.year == 2024


class TestCrossref:
    def test_an_item_becomes_a_paper(self):
        paper = paper_from_crossref(
            CrossrefItem.model_validate(
                {
                    "title": ["A Crossref Work"],
                    "DOI": "10.1/cr",
                    "issued": {"date-parts": [[2022, 4]]},
                    "author": [{"given": "Grace", "family": "Hopper"}],
                    "container-title": ["Journal of Things"],
                }
            )
        )
        assert paper.title == "A Crossref Work"
        assert paper.doi == "10.1/cr"
        assert paper.year == 2022
        assert paper.venue == "Journal of Things"
        assert paper.authors == ("Grace Hopper",)

    def test_a_title_less_item_is_marked_untitled(self):
        item = CrossrefItem.model_validate({"DOI": "10.1/x"})
        assert paper_from_crossref(item).title == "(untitled)"
