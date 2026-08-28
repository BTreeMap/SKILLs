"""Session storage: criteria gating, atomic writes, and corpus round trips."""

from __future__ import annotations

import json

import pytest

from btm_corekit import CommandError
from btm_lit_review.paper import candidate
from btm_lit_review.session import (
    Session,
    append_log,
    atomic_write,
    criteria_hash,
    load_papers,
    load_protocol,
    read_log,
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


class TestCriteriaGate:
    def test_empty_criteria_are_refused(self):
        with pytest.raises(CommandError):
            require_criteria({"criteria": {}})

    def test_an_empty_exclude_list_is_refused(self):
        """Both lists must be filled: criteria precede search."""
        with pytest.raises(CommandError):
            require_criteria({"criteria": {"include": ["about X"], "exclude": []}})

    def test_both_lists_filled_pass(self):
        require_criteria({"criteria": {"include": ["about X"], "exclude": ["not X"]}})

    def test_the_hash_is_stable_for_equal_criteria(self):
        one = {"criteria": {"include": ["a"], "exclude": ["b"]}}
        two = {"criteria": {"include": ["a"], "exclude": ["b"]}}
        assert criteria_hash(one) == criteria_hash(two)

    def test_the_hash_moves_when_criteria_change(self):
        one = {"criteria": {"include": ["a"]}}
        two = {"criteria": {"include": ["a", "c"]}}
        assert criteria_hash(one) != criteria_hash(two)


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
        assert load_protocol(session)["question"] == "q"


class TestLog:
    def test_entries_append_in_order(self, session):
        append_log(session, {"query": "one"})
        append_log(session, {"query": "two"})
        assert [entry["query"] for entry in read_log(session)] == ["one", "two"]

    def test_an_empty_log_reads_as_empty(self, session):
        assert read_log(session) == []


class TestAtomicWrite:
    def test_the_file_is_replaced_whole(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_text("before", encoding="utf-8")
        atomic_write(path, "after")
        assert path.read_text(encoding="utf-8") == "after"

    def test_no_temporary_file_survives(self, tmp_path):
        path = tmp_path / "f.json"
        atomic_write(path, "text")
        assert [p.name for p in tmp_path.iterdir()] == ["f.json"]
