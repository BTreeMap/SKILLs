"""Upstream normalization: one record per source becomes one Paper."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from btm_lit_review.upstream import (
    paper_from_arxiv,
    paper_from_crossref,
    paper_from_openalex,
    reconstruct_abstract,
)

ARXIV_ENTRY = """<entry xmlns="http://www.w3.org/2005/Atom"
                        xmlns:arxiv="http://arxiv.org/schemas/atom">
  <id>http://arxiv.org/abs/2401.01234v2</id>
  <title>A Study of Things</title>
  <summary>We study things.</summary>
  <published>2024-01-05T00:00:00Z</published>
  <author><name>Ada Lovelace</name></author>
  <arxiv:doi>10.1/xyz</arxiv:doi>
</entry>"""


class TestInvertedAbstract:
    def test_positions_rebuild_the_original_word_order(self):
        assert reconstruct_abstract({"Hello": [0], "world": [1]}) == "Hello world"

    def test_a_repeated_word_lands_at_every_position(self):
        assert reconstruct_abstract({"a": [0, 2], "b": [1]}) == "a b a"

    def test_an_absent_index_yields_absence(self):
        assert reconstruct_abstract(None) is None


class TestOpenAlex:
    def test_a_work_becomes_a_paper_with_its_identifiers(self):
        work = {
            "display_name": "A Study",
            "doi": "https://doi.org/10.1/abc",
            "publication_year": 2023,
            "cited_by_count": 7,
            "authorships": [{"author": {"display_name": "Ada"}}],
        }
        paper = paper_from_openalex(work)
        assert paper.title == "A Study"
        assert paper.doi == "10.1/abc"
        assert paper.year == 2023
        assert paper.authors == ("Ada",)

    def test_a_sparse_work_still_parses(self):
        assert paper_from_openalex({"display_name": "Bare"}).title == "Bare"

    def test_a_work_without_a_name_is_marked_untitled(self):
        """The corpus never holds a blank title; absence is stated instead."""
        assert paper_from_openalex({}).title == "(untitled)"


class TestArxiv:
    def test_an_entry_becomes_a_paper(self):
        paper = paper_from_arxiv(ET.fromstring(ARXIV_ENTRY))
        assert paper.title == "A Study of Things"
        assert paper.arxiv_id == "2401.01234"
        assert paper.doi == "10.1/xyz"
        assert paper.authors == ("Ada Lovelace",)
        assert paper.year == 2024


class TestCrossref:
    def test_an_item_becomes_a_paper(self):
        item = {
            "title": ["A Crossref Work"],
            "DOI": "10.1/cr",
            "issued": {"date-parts": [[2022, 4]]},
            "author": [{"given": "Grace", "family": "Hopper"}],
            "container-title": ["Journal of Things"],
        }
        paper = paper_from_crossref(item)
        assert paper.title == "A Crossref Work"
        assert paper.doi == "10.1/cr"
        assert paper.year == 2022
        assert paper.venue == "Journal of Things"

    def test_a_title_less_item_is_marked_untitled(self):
        assert paper_from_crossref({"DOI": "10.1/x"}).title == "(untitled)"
