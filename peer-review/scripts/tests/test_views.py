"""Derived standings, the recommendation rule, the echo ratio, cite-check."""

from __future__ import annotations

from btm_peer_review.constants import Standing
from btm_peer_review.ledger import replay
from btm_peer_review.store import load_corpus
from btm_peer_review.text import PaperText
from btm_peer_review.views import (
    cite_check,
    claim_views,
    coverage,
    echo_ratio,
    objection_views,
    recommendation,
    scaffold,
)


def objection(oid, kind, severity, anchors=(), prior=(), claim=None):  # noqa: PLR0913, PLR0917 - a test row reads best flat
    return {
        "e": "objection",
        "id": oid,
        "kind": kind,
        "severity": severity,
        "text": "t",
        "claim": claim,
        "anchors": list(anchors),
        "prior": list(prior),
    }


EVENTS = [
    {
        "e": "claim",
        "id": "c-first",
        "verbatim": "the first to combine bandits with prompt selection",
        "page": 1,
    },
    objection(
        "o-seeds",
        "selective",
        "major",
        ["We report the best run over five seeds"],
        claim="c-first",
    ),
    objection("o-english", "shallow", "minor", ["Our evaluation covers English only"]),
    objection(
        "o-first",
        "first",
        "major",
        ["the first to combine bandits"],
        prior=["doi:10.1/a"],
        claim="c-first",
    ),
    objection("o-gone", "control", "fatal", ["text that is not in the paper anywhere"]),
    {"e": "walk", "bank": "design", "note": ""},
]


def derive(paper, corpus_dir=None, year=2026, events=EVENTS):
    ledger = replay(events)
    corpus = load_corpus(corpus_dir / "papers.jsonl") if corpus_dir else None
    objections = objection_views(ledger, paper, corpus, year)
    return ledger, paper, corpus, objections, claim_views(ledger, paper, objections)


class TestStandings:
    def test_each_standing_derives_from_live_state(self, paper_text, corpus_dir):
        _, _, _, objections, claims = derive(paper_text, corpus_dir)
        standing = {v["marker"]: v["standing"] for v in objections}
        assert standing == {
            "O1": "grounded",
            "O2": "grounded",
            "O3": "grounded",
            "O4": "unanchored",
        }
        assert claims[0]["verdict"] == "contested"
        assert claims[0]["objections"] == ["O1", "O3"]

    def test_novelty_without_a_corpus_is_undated(self, paper_text):
        _, _, _, objections, _ = derive(paper_text)
        assert objections[2]["standing"] == "undated"

    def test_a_prior_that_postdates_the_paper_is_undated(self, paper_text, corpus_dir):
        _, _, _, objections, _ = derive(paper_text, corpus_dir, year=2020)
        assert objections[2]["standing"] == "undated"

    def test_withdrawal_wins_over_grounding(self, paper_text, corpus_dir):
        events = [
            *EVENTS,
            {"e": "withdraw", "objection": "o-seeds", "reason": "mean in appendix"},
        ]
        _, _, _, objections, claims = derive(paper_text, corpus_dir, events=events)
        assert objections[0]["standing"] == "withdrawn"
        assert claims[0]["objections"] == ["O3"]


class TestRules:
    def test_recommendation_follows_the_worst_grounded_severity(
        self, paper_text, corpus_dir
    ):
        _, _, _, objections, _ = derive(paper_text, corpus_dir)
        assert recommendation(objections)["verdict"] == "major revision"
        only_minor = [v for v in objections if v["marker"] == "O2"]
        assert recommendation(only_minor)["verdict"] == "minor revision"
        assert recommendation([])["verdict"] == "no objection stands"
        fatal = [dict(objections[3], standing=Standing.GROUNDED)]
        assert recommendation(fatal)["verdict"] == "reject"

    def test_echo_ratio_counts_anchors_inside_limitations(self, paper_text, corpus_dir):
        _, paper, _, objections, _ = derive(paper_text, corpus_dir)
        echo = echo_ratio(objections, paper)
        assert echo["inside"] == 1 and echo["anchored"] == 3
        assert echo["warn"] is False
        assert echo_ratio(objections, PaperText([(1, "no heading")]))["ratio"] is None

    def test_coverage_names_unwalked_banks_for_the_level(self, paper_text, corpus_dir):
        ledger, paper, corpus, _, _ = derive(paper_text, corpus_dir)
        full = coverage(ledger, "full", corpus, paper)
        assert full["walked"] == ["design"]
        assert "novelty" in full["unwalked"] and full["confidence"] == "low"
        lite = coverage(
            replay(
                [
                    *EVENTS,
                    {"e": "walk", "bank": "claims"},
                    {"e": "walk", "bank": "limitations"},
                ]
            ),
            "lite",
            None,
            paper,
        )
        assert lite["confidence"] == "high"

    def test_scaffold_groups_grounded_by_severity(self, paper_text, corpus_dir):
        _, _, _, objections, claims = derive(paper_text, corpus_dir)
        shape = scaffold(claims, objections)
        assert shape["major"] == ["O1", "O3"] and shape["minor"] == ["O2"]
        assert shape["unanchored"] == ["O4"] and shape["fatal"] == []


class TestCiteCheck:
    def test_draft_markers_must_resolve_and_majors_must_appear(
        self, paper_text, corpus_dir
    ):
        _, _, _, objections, claims = derive(paper_text, corpus_dir)
        report = cite_check(
            "[C1] fails per [O1] and [O4]; see [O9].", claims, objections
        )
        assert report["markers"] == 4
        assert any("[O4] is unanchored" in p for p in report["problems"])
        assert any("[O9] was never minted" in p for p in report["problems"])
        assert any("[O3] is a grounded major" in p for p in report["problems"])
        clean = cite_check("[O1] [O3]", claims, objections)
        assert clean["problems"] == []
