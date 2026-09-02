"""The gate: one verdict carries every problem; the ledger changes only on success."""

from __future__ import annotations

import pytest

from btm_peer_review.batch import Context, expand_batch
from btm_peer_review.state import Ledger
from btm_peer_review.store import load_corpus


def fake_mint(words):
    return "-".join(words) + "-x"


@pytest.fixture
def admit(paper_text):
    def run(batch, *, ledger=None, corpus=None, year=2026, text=paper_text):
        ledger = ledger if ledger is not None else Ledger()
        return ledger, expand_batch(
            ledger, batch, Context(text, corpus, year), fake_mint
        )

    return run


CLAIM = {
    "kw": ["first", "combine"],
    "verbatim": "Our method is the first to combine bandits with prompt selection.",
}
SEEDS = {
    "kw": ["best", "run"],
    "kind": "selective",
    "severity": "major",
    "text": "Best-of-five reporting; report mean and spread.",
    "anchors": ["We report the best run over five seeds"],
}


class TestClaims:
    def test_a_verbatim_claim_is_admitted_with_its_page(self, admit):
        ledger, result = admit({"claims": [CLAIM]})
        assert not result.problems
        assert result.minted["claims"] == {"first-combine": "first-combine-x"}
        assert ledger.claims["first-combine-x"].page == 1

    def test_a_paraphrase_is_rejected_with_the_closest_page(self, admit):
        ledger, result = admit(
            {
                "claims": [
                    {
                        "kw": ["a", "b"],
                        "verbatim": "Our method is the first ever to merge "
                        "bandits and prompt choosing",
                    }
                ]
            }
        )
        assert ledger.claims == {}
        [problem] = result.problems
        assert problem.where == "claims[0].verbatim"
        assert "closest page 1" in problem.hint

    def test_without_ingest_every_quote_fails(self, admit):
        _, result = admit({"claims": [CLAIM]}, text=None)
        assert "ingest" in result.problems[0].fix


class TestObjections:
    def test_anchored_objection_targets_a_claim_minted_in_the_same_batch(self, admit):
        ledger, result = admit(
            {"claims": [CLAIM], "objections": [{**SEEDS, "claim": "first combine"}]}
        )
        assert not result.problems
        objection = ledger.objections["best-run-x"]
        assert objection.claim == "first-combine-x"
        assert objection.evidence.anchors == ("We report the best run over five seeds",)

    def test_missing_replaces_anchors(self, admit):
        ledger, result = admit(
            {
                "objections": [
                    {
                        "kw": ["error", "bars"],
                        "kind": "variance",
                        "severity": "major",
                        "text": "No spread reported.",
                        "missing": "error bars or confidence intervals for Table 1",
                    }
                ]
            }
        )
        assert not result.problems
        assert ledger.objections["error-bars-x"].evidence.what.startswith("error bars")

    def test_every_problem_comes_back_at_once(self, admit):
        ledger, result = admit(
            {
                "objections": [
                    {
                        "kw": ["x", "y"],
                        "kind": "vibes",
                        "severity": "huge",
                        "text": "",
                        "anchors": ["not in the paper at all here"],
                    }
                ],
                "bogus": [],
            }
        )
        where = {p.where for p in result.problems}
        assert {
            "objections[0].kind",
            "objections[0].severity",
            "objections[0].text",
            "objections[0].anchors[0]",
            "bogus",
        } <= where
        assert ledger.objections == {}
        assert result.events == []

    def test_novelty_needs_a_linked_corpus_and_dated_prior(self, admit, corpus_dir):
        base = {
            "kw": ["not", "first"],
            "kind": "first",
            "severity": "major",
            "text": "Bandit routing predates this.",
            "anchors": ["the first to combine bandits"],
        }
        _, result = admit({"objections": [base]})
        assert "novelty objection names the prior work" in result.problems[0].fix
        corpus = load_corpus(corpus_dir / "papers.jsonl")
        _, result = admit(
            {
                "objections": [
                    {**base, "prior": ["doi:10.1/b", "title:undated router", "nope"]}
                ]
            },
            corpus=corpus,
        )
        fixes = " ".join(p.fix for p in result.problems)
        assert (
            "postdates" in fixes
            and "no year" in fixes
            and "not in the linked corpus" in fixes
        )
        ledger, result = admit(
            {"objections": [{**base, "prior": ["DOI:10.1/a"]}]},
            corpus=corpus,
        )
        assert not result.problems
        assert ledger.objections["not-first-x"].prior == ("DOI:10.1/a",)


class TestWalksAndWithdraws:
    def test_walk_and_withdraw_round_trip(self, admit):
        ledger, result = admit(
            {
                "objections": [SEEDS],
                "walks": [{"bank": "design", "note": "seeds and baselines checked"}],
            }
        )
        assert not result.problems
        assert ledger.walks == {"design": "seeds and baselines checked"}
        ledger, result = admit(
            {
                "withdraws": [
                    {"objection": "best run", "reason": "appendix B reports the mean"}
                ]
            },
            ledger=ledger,
        )
        assert not result.problems
        assert ledger.withdrawn == {"best-run-x": "appendix B reports the mean"}

    def test_prior_keys_outside_the_novelty_bank_are_refused(self, admit):
        _, result = admit({"objections": [{**SEEDS, "prior": ["doi:10.1/a"]}]})
        assert result.problems[0].where == "objections[0].prior"

    def test_unknown_bank_and_empty_batch_are_rejected(self, admit):
        _, result = admit({"walks": [{"bank": "vibes"}]})
        assert result.problems[0].where == "walks[0].bank"
        _, result = admit({})
        assert result.problems[0].where == "$"
