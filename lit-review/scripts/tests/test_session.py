"""Session storage: criteria gating, atomic writes, and corpus round trips."""

from __future__ import annotations

import json

import pytest

from btm_corekit import CommandError
from btm_lit_review.paper import candidate
from btm_lit_review.session import (
    Criteria,
    Protocol,
    Session,
    criteria_hash,
    load_papers,
    load_protocol,
    require_criteria,
    save_papers,
)


@pytest.fixture
def session(tmp_path):
    root = tmp_path / "review"
    root.mkdir()
    (root / "protocol.json").write_text(
        json.dumps({"question": "q", "level": "full", "criteria": {}}), encoding="utf-8"
    )
    (root / "papers.jsonl").touch()
    (root / "search_log.jsonl").touch()
    return Session(root=root)


def framed(**criteria) -> Protocol:
    return Protocol(question="q", criteria=Criteria(**criteria))


class TestCriteriaGate:
    def test_empty_criteria_are_refused(self):
        with pytest.raises(CommandError):
            require_criteria(framed())

    def test_an_empty_exclude_list_is_refused(self):
        """Both lists must be filled: criteria precede search."""
        with pytest.raises(CommandError):
            require_criteria(framed(include=["about X"]))

    def test_both_lists_filled_pass(self):
        require_criteria(framed(include=["about X"], exclude=["not X"]))

    def test_the_hash_is_stable_for_equal_criteria(self):
        one = framed(include=["a"], exclude=["b"])
        two = framed(include=["a"], exclude=["b"])
        assert criteria_hash(one) == criteria_hash(two)

    def test_the_hash_moves_when_criteria_change(self):
        assert criteria_hash(framed(include=["a"])) != criteria_hash(
            framed(include=["a", "c"])
        )


class TestCorpusRoundTrip:
    def test_saved_papers_load_back_equal(self, session):
        record = candidate(
            title="T",
            year=None,
            authors=(),
            venue=None,
            doi="10.1/a",
            arxiv_id=None,
            openalex_id=None,
            cited_by_count=None,
            abstract=None,
            pdf_url=None,
            landing_url=None,
        )
        papers = {record.key: record}
        save_papers(session, papers)
        assert load_papers(session) == papers

    def test_an_empty_corpus_loads_as_empty(self, session):
        assert load_papers(session) == {}

    def test_a_corrupt_line_is_refused_rather_than_skipped(self, session):
        session.papers_path.write_text('{"key": "x"}\n', encoding="utf-8")
        with pytest.raises(CommandError):
            load_papers(session)

    def test_the_protocol_reads_back(self, session):
        assert load_protocol(session).question == "q"
