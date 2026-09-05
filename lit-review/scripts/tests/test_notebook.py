"""Notebook admission and the derived verdicts over live corpus state."""

from __future__ import annotations

import pytest

from btm_corekit import Work
from btm_lit_review.constants import ReadLevel, Status
from btm_lit_review.corpus.paper import paper_from
from btm_lit_review.findings.notebook import (
    WATCH_MAX,
    FindingRecord,
    GapRecord,
    arrivals_of,
    expand_notes,
    finding_view,
    gap_view,
    live,
    next_id,
    watch_hits,
    watch_terms,
)


@pytest.fixture
def papers():
    bandit = paper_from(
        Work(
            title="Bandit routing",
            year=2024,
            authors=("A",),
            venue=None,
            doi="10.1/bandit",
            arxiv_id=None,
            openalex_id=None,
            cited_by=3,
            abstract="combinatorial bandit",
            pdf_url=None,
            landing_url=None,
            published=None,
        )
    )
    flow = paper_from(
        Work(
            title="GFlowNet sampling",
            year=2025,
            authors=("B",),
            venue=None,
            doi=None,
            arxiv_id="2501.00001",
            openalex_id=None,
            cited_by=1,
            abstract="gflownet sampler",
            pdf_url=None,
            landing_url=None,
            published=None,
        )
    )
    bandit = bandit.with_(
        status=Status.INCLUDED, read_level=ReadLevel.FULL_TEXT, found_by=("s1",)
    )
    flow = flow.with_(
        status=Status.INCLUDED, read_level=ReadLevel.ABSTRACT, found_by=("s3",)
    )
    return {bandit.key: bandit, flow.key: flow}


def expand(batch, papers, log_count=3, pad=frozenset(), existing=()):
    return expand_notes(batch, papers, log_count, set(pad), list(existing))


class TestAdmission:
    def test_a_clean_batch_mints_ids_and_stamps_defaults(self, papers):
        result = expand(
            {
                "findings": [
                    {"claim": "routing is cheap", "support": ["doi:10.1/bandit"]}
                ],
                "gaps": [{"statement": "no combined system", "probes": ["s2"]}],
            },
            papers,
        )
        assert result.problems == []
        assert result.admitted == {"findings": ["f1"], "gaps": ["g1"]}
        finding, gap = result.records
        assert finding["support"] == [{"key": "doi:10.1/bandit", "needs": "full-text"}]
        assert gap["seen"] == 3

    def test_every_problem_arrives_in_one_verdict(self, papers):
        result = expand(
            {
                "findings": [{"claim": "", "support": ["doi:10.9/ghost"]}],
                "gaps": [{"statement": "x", "probes": ["s9"], "watch": " | "}],
                "extra": [],
            },
            papers,
        )
        wheres = {problem.where for problem in result.problems}
        assert {
            "findings[0].claim",
            "findings[0].support[0]",
            "gaps[0].probes[0]",
            "gaps[0].watch",
            "extra",
        } <= wheres
        assert result.records == []

    def test_support_resolves_aliases_with_an_advisory(self, papers):
        result = expand(
            {"findings": [{"claim": "c", "support": ["10.1/bandit", "2501.00001"]}]},
            papers,
        )
        assert result.problems == []
        keys = [s["key"] for s in result.records[0]["support"]]
        assert keys == ["doi:10.1/bandit", "arxiv:2501.00001"]
        assert len(result.advisories) == 2

    def test_unknown_fields_are_sent_to_the_pad(self, papers):
        result = expand(
            {
                "findings": [
                    {"claim": "c", "support": ["doi:10.1/bandit"], "mood": "sunny"}
                ]
            },
            papers,
        )
        assert any("pad" in (p.hint or "") for p in result.problems)

    def test_a_gap_without_probes_is_advised_and_admitted(self, papers):
        result = expand({"gaps": [{"statement": "nothing combines them"}]}, papers)
        assert result.problems == []
        assert any("probe evidence" in line for line in result.advisories)

    def test_dangling_pad_and_supersede_refs_are_refused(self, papers):
        result = expand(
            {
                "findings": [
                    {
                        "claim": "c",
                        "support": ["doi:10.1/bandit"],
                        "from": ["j9"],
                        "supersedes": "f7",
                    }
                ]
            },
            papers,
            pad={"j1"},
        )
        wheres = {problem.where for problem in result.problems}
        assert wheres == {"findings[0].from[0]", "findings[0].supersedes"}

    def test_an_empty_batch_records_nothing(self, papers):
        result = expand({}, papers)
        assert [p.where for p in result.problems] == ["$"]


class TestDerivedVerdicts:
    def finding(self, needs="full-text"):
        return FindingRecord(
            e="finding",
            id="f1",
            claim="c",
            support=[{"key": "doi:10.1/bandit", "needs": needs}],
        )

    def test_supported_while_the_corpus_agrees(self, papers):
        assert finding_view(self.finding(), papers)["state"] == "supported"

    def test_at_risk_when_support_is_excluded(self, papers):
        papers = dict(papers)
        papers["doi:10.1/bandit"] = papers["doi:10.1/bandit"].with_(
            status=Status.EXCLUDED, decision_reason="off topic"
        )
        view = finding_view(self.finding(), papers)
        assert view["state"] == "at-risk"
        assert "excluded" in view["issues"][0]

    def test_at_risk_when_read_below_the_floor(self, papers):
        papers = dict(papers)
        papers["doi:10.1/bandit"] = papers["doi:10.1/bandit"].with_(
            read_level=ReadLevel.ABSTRACT
        )
        view = finding_view(self.finding(), papers)
        assert "needs full-text" in view["issues"][0]

    def test_a_gap_is_challenged_by_a_later_watch_hit(self, papers):
        gap = GapRecord(e="gap", id="g1", statement="s", seen=2, watch="gflownet")
        view = gap_view(gap, arrivals_of(papers))
        assert view["state"] == "challenged"
        assert view["hits"] == ["arxiv:2501.00001"]

    def test_papers_seen_before_the_gap_never_challenge_it(self, papers):
        gap = GapRecord(
            e="gap", id="g1", statement="s", seen=3, watch="gflownet|bandit"
        )
        assert gap_view(gap, arrivals_of(papers))["state"] == "standing"


def found(ident, supersedes=None):
    return FindingRecord(
        e="finding",
        id=ident,
        claim="c",
        support=[{"key": "k", "needs": "abstract"}],
        supersedes=supersedes,
    )


class TestSupersedeChains:
    def test_live_keeps_the_latest_of_a_chain(self):
        records = [
            found("f1"),
            found("f2", supersedes="f1"),
            GapRecord(e="gap", id="g1", statement="s"),
        ]
        assert set(live(records, FindingRecord)) == {"f2"}
        assert set(live(records, GapRecord)) == {"g1"}

    def test_ids_count_every_record_ever_minted(self):
        records = [found("f1"), found("f2", supersedes="f1")]
        assert next_id(records, "finding") == "f3"
        assert next_id(records, "rule") == "r1"


def test_an_overlong_watch_is_refused():
    batch = {"gaps": [{"statement": "s", "probes": [], "watch": "a" * (WATCH_MAX + 1)}]}
    result = expand_notes(batch, {}, 0, set(), [])
    assert result.records == []
    assert result.problems[0].where == "gaps[0].watch"


def test_a_watch_matches_its_words_literally():
    terms = [term.casefold() for term in watch_terms("retrieval augmented | a+b")]
    assert watch_hits(terms, "a retrieval augmented sampler".casefold())
    assert watch_hits(terms, "uses a+b") and not watch_hits(terms, "uses aab")
