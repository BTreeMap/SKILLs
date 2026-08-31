"""Markers stay monotone; cite-check judges a draft mechanically."""

from __future__ import annotations

from dataclasses import replace

import pytest

from btm_lit_review.draft import assign_markers, cite_check, marker_table
from btm_lit_review.paper import candidate


def paper(title, doi, status="included", read_level="abstract"):
    built = candidate(
        title=title,
        year=2024,
        authors=(),
        venue=None,
        doi=doi,
        arxiv_id=None,
        openalex_id=None,
        cited_by_count=None,
        abstract=None,
        pdf_url=None,
        landing_url=None,
    )
    return replace(built, status=status, read_level=read_level)


@pytest.fixture
def papers():
    one = paper("First", "10.1/a")
    two = paper("Second", "10.1/b")
    out = paper("Cut", "10.1/c", status="excluded")
    return {p.key: p for p in (one, two, out)}


class TestAssignMarkers:
    def test_included_papers_are_numbered_in_corpus_order(self, papers):
        assert assign_markers({}, papers) == {"doi:10.1/a": 1, "doi:10.1/b": 2}

    def test_existing_numbers_never_move(self, papers):
        markers = assign_markers({"doi:10.1/b": 1}, papers)
        assert markers == {"doi:10.1/b": 1, "doi:10.1/a": 2}

    def test_a_late_inclusion_extends_the_map(self, papers):
        first = assign_markers({}, papers)
        papers["doi:10.1/c"] = replace(papers["doi:10.1/c"], status="included")
        assert assign_markers(first, papers)["doi:10.1/c"] == 3


class TestCiteCheck:
    def test_a_clean_draft_passes(self, papers):
        markers = assign_markers({}, papers)
        report = cite_check("First [1] and second [2].", markers, papers, [])
        assert report["problems"] == []
        assert report["unused_included"] == []

    def test_every_problem_class_is_named(self, papers):
        papers["doi:10.1/b"] = replace(papers["doi:10.1/b"], read_level="none")
        markers = assign_markers({}, papers) | {"doi:10.1/c": 3}
        report = cite_check("[1] [2] [3] [9]", markers, papers, [])
        assert any("unread" in p for p in report["problems"])
        assert any("excluded" in p for p in report["problems"])
        assert any("never assigned" in p for p in report["problems"])

    def test_unused_included_papers_are_listed(self, papers):
        markers = assign_markers({}, papers)
        report = cite_check("only [1]", markers, papers, [])
        assert report["unused_included"] == ["[2]"]

    def test_at_risk_findings_ride_along(self, papers):
        views = [{"id": "f1", "state": "at-risk"}, {"id": "f2", "state": "supported"}]
        report = cite_check("[1]", assign_markers({}, papers), papers, views)
        assert [f["id"] for f in report["at_risk_findings"]] == ["f1"]


class TestMarkerTable:
    def test_rows_are_keyed_by_rendered_marker_in_number_order(self, papers):
        markers = assign_markers({}, papers)
        table = marker_table(markers, papers)
        assert list(table) == ["[1]", "[2]"]
        assert table["[1]"]["title"] == "First"
