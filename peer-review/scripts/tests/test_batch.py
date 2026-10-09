"""The gate: one verdict carries every problem; the ledger changes only on success."""

from __future__ import annotations

import pytest

from btm_peer_review.batch import Context, expand_batch
from btm_peer_review.state import Ledger
from btm_peer_review.store import load_corpus


def fake_mint(words):
    return "-".join(words) + "-x"


@pytest.fixture
def accept(paper_text):
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
    "type": "selective",
    "severity": "major",
    "text": "Best-of-five reporting; report mean and spread.",
    "anchors": ["We report the best run over five seeds"],
}


class TestClaims:
    def test_a_verbatim_claim_is_accepted_with_its_page(self, accept):
        ledger, result = accept({"claims": [CLAIM]})
        assert not result.problems
        assert result.new["claims"] == {"first-combine": "first-combine-x"}
        assert ledger.claims["first-combine-x"].page == 1

    def test_a_paraphrase_is_rejected_with_the_closest_page(self, accept):
        ledger, result = accept(
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

    def test_without_ingest_every_quote_fails(self, accept):
        _, result = accept({"claims": [CLAIM]}, text=None)
        assert "ingest" in result.problems[0].fix


class TestObjections:
    def test_anchored_objection_targets_a_claim_made_in_the_same_batch(self, accept):
        ledger, result = accept(
            {"claims": [CLAIM], "objections": [{**SEEDS, "claim": "first combine"}]}
        )
        assert not result.problems
        objection = ledger.objections["best-run-x"]
        assert objection.claim == "first-combine-x"
        assert objection.evidence.anchors == ("We report the best run over five seeds",)

    def test_missing_replaces_anchors(self, accept):
        ledger, result = accept(
            {
                "objections": [
                    {
                        "kw": ["error", "bars"],
                        "type": "variance",
                        "severity": "major",
                        "text": "No spread reported.",
                        "missing": "error bars or confidence intervals for Table 1",
                    }
                ]
            }
        )
        assert not result.problems
        assert ledger.objections["error-bars-x"].evidence.what.startswith("error bars")

    def test_every_problem_comes_back_at_once(self, accept):
        ledger, result = accept(
            {
                "objections": [
                    {
                        "kw": ["x", "y"],
                        "type": "vibes",
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
            "objections[0].type",
            "objections[0].severity",
            "objections[0].text",
            "objections[0].anchors[0]",
            "bogus",
        } <= where
        assert ledger.objections == {}
        assert result.events == []

    def test_a_malformed_family_never_hides_a_problem_in_its_siblings(self, accept):
        """A container of the wrong shape once swallowed the whole batch, so
        the unanchored quote beside it cost a second round trip."""
        _, result = accept(
            {
                "claims": CLAIM,
                "objections": [{**SEEDS, "anchors": ["not in the paper at all here"]}],
            }
        )
        assert {p.where for p in result.problems} == {
            "claims",
            "objections[0].anchors[0]",
        }

    def test_novelty_needs_a_attached_corpus_and_dated_prior(self, accept, corpus_dir):
        base = {
            "kw": ["not", "first"],
            "type": "first",
            "severity": "major",
            "text": "Bandit routing predates this.",
            "anchors": ["the first to combine bandits"],
        }
        _, result = accept({"objections": [base]})
        assert "novelty objection names the prior work" in result.problems[0].fix
        corpus = load_corpus(corpus_dir / "papers.jsonl")
        _, result = accept(
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
            and "not in the attached corpus" in fixes
        )
        ledger, result = accept(
            {"objections": [{**base, "prior": ["DOI:10.1/a"]}]},
            corpus=corpus,
        )
        assert not result.problems
        assert ledger.objections["not-first-x"].prior == ("DOI:10.1/a",)


class TestWalksAndWithdraws:
    def test_walk_and_withdraw_round_trip(self, accept):
        ledger, result = accept(
            {
                "objections": [SEEDS],
                "walks": [{"bank": "design", "note": "seeds and baselines checked"}],
            }
        )
        assert not result.problems
        assert ledger.walks == {"design": "seeds and baselines checked"}
        ledger, result = accept(
            {
                "withdraws": [
                    {"objection": "best run", "reason": "appendix B reports the mean"}
                ]
            },
            ledger=ledger,
        )
        assert not result.problems
        assert ledger.withdrawn == {"best-run-x": "appendix B reports the mean"}

    def test_prior_keys_outside_the_novelty_bank_are_refused(self, accept):
        _, result = accept({"objections": [{**SEEDS, "prior": ["doi:10.1/a"]}]})
        assert result.problems[0].where == "objections[0].prior"

    def test_unknown_bank_and_empty_batch_are_rejected(self, accept):
        _, result = accept({"walks": [{"bank": "vibes"}]})
        assert result.problems[0].where == "walks[0].bank"
        _, result = accept({})
        assert result.problems[0].where == "$"
