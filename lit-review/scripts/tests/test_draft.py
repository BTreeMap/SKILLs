"""Markers stay monotone; cite-check judges a draft mechanically."""

from __future__ import annotations

import re

import pytest

from btm_corekit import CommandError, Work
from btm_lit_review.constants import ReadLevel, Status
from btm_lit_review.corpus.paper import paper_from
from btm_lit_review.findings.draft import (
    assign_markers,
    cite_check,
    load_markers,
    marker_table,
)
from btm_lit_review.session import Session


def paper(
    title,
    doi,
    status=Status.INCLUDED,
    read_level=ReadLevel.ABSTRACT,
    decision_reason=None,
):
    built = paper_from(
        Work(
            title=title,
            year=2024,
            authors=(),
            venue=None,
            doi=doi,
            arxiv_id=None,
            openalex_id=None,
            cited_by=None,
            abstract=None,
            pdf_url=None,
            landing_url=None,
            published=None,
        )
    )
    return built.with_(
        status=status, read_level=read_level, decision_reason=decision_reason
    )


@pytest.fixture
def papers():
    one = paper("First", "10.1/a")
    two = paper("Second", "10.1/b")
    out = paper("Cut", "10.1/c", status=Status.EXCLUDED, decision_reason="off topic")
    return {p.key: p for p in (one, two, out)}


class TestAssignMarkers:
    def test_included_papers_are_numbered_in_corpus_order(self, papers):
        assert assign_markers({}, papers) == {"doi:10.1/a": 1, "doi:10.1/b": 2}

    def test_existing_numbers_never_move(self, papers):
        markers = assign_markers({"doi:10.1/b": 1}, papers)
        assert markers == {"doi:10.1/b": 1, "doi:10.1/a": 2}

    def test_a_late_inclusion_extends_the_map(self, papers):
        first = assign_markers({}, papers)
        papers["doi:10.1/c"] = papers["doi:10.1/c"].with_(status=Status.INCLUDED)
        assert assign_markers(first, papers)["doi:10.1/c"] == 3


class TestCiteCheck:
    def test_a_clean_draft_passes(self, papers):
        markers = assign_markers({}, papers)
        report = cite_check("First [1] and second [2].", markers, papers, [])
        assert report["problems"] == []
        assert report["unused_included"] == []

    def test_every_problem_class_is_named(self, papers):
        papers["doi:10.1/b"] = papers["doi:10.1/b"].with_(read_level=ReadLevel.NONE)
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

    def test_a_marker_quoted_inside_code_is_not_a_citation(self, papers):
        """A draft that shows the agent how to cite would otherwise count its
        own example, and a fenced command could go on to cite a cut paper."""
        markers = assign_markers({}, papers) | {"doi:10.1/c": 3}
        draft = "First [1].\n```\nwrite [2] and [3]\n```\nInline `[9]`.\n"
        report = cite_check(draft, markers, papers, [])
        assert report["citations"] == 1
        assert report["problems"] == []
        assert report["unused_included"] == ["[2]"]


class TestLoadMarkers:
    """citations.json is authoritative: it is the draft's only handle on a
    paper, so a file that will not decode refuses by name."""

    def session(self, tmp_path, written):
        (tmp_path / "citations.json").write_text(written, encoding="utf-8")
        return Session(root=tmp_path)

    def test_an_absent_file_is_an_empty_map(self, tmp_path):
        assert load_markers(Session(root=tmp_path)) == {}

    def test_a_written_map_reads_back(self, tmp_path):
        assert load_markers(self.session(tmp_path, '{"doi:10.1/a": 1}')) == {
            "doi:10.1/a": 1
        }

    @pytest.mark.parametrize("written", ["{", '{"doi:10.1/a": "one"}', "[1, 2]"])
    def test_anything_undecodable_names_the_file(self, tmp_path, written):
        with pytest.raises(CommandError, match=re.escape("citations.json")):
            load_markers(self.session(tmp_path, written))


class TestMarkerTable:
    def test_rows_are_keyed_by_rendered_marker_in_number_order(self, papers):
        markers = assign_markers({}, papers)
        table = marker_table(markers, papers)
        assert list(table) == ["[1]", "[2]"]
        assert table["[1]"]["title"] == "First"
