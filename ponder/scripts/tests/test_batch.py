"""The note pipeline: minting, references, recovery, and total rejection."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from btm_corekit import slugify, suggest
from btm_ponder.batch import expand_batch
from btm_ponder.state import Ledger, Retrieved


def fixed_mint(words: Iterable[str]) -> str:
    """Deterministic stand-in for mint, so expansion is assertable."""
    return slugify(words) + "-0123456789abcdefghijklmnop"[:32]


BCL_URL = "https://example.org/bcl"

FULL_BATCH = {
    "leaves": [
        {"kw": ["rent", "length"], "q": "what does Rent guarantee"},
        {"kw": ["pool", "clear"], "q": "clearArray semantics", "origin": "spawned"},
        {"kw": ["memory", "pool"], "q": "when to prefer MemoryPool"},
    ],
    "sources": [
        {
            "kw": ["bcl", "rent"],
            "leaf": "rent length",
            "cls": "constitutive",
            "title": "BCL source",
            "url": BCL_URL,
        },
        {
            "kw": ["blog", "folk"],
            "leaf": "clear",
            "cls": "reported",
            "title": "folk belief post",
        },
    ],
    "closes": [
        {
            "leaf": "rent length",
            "state": "retrieved",
            "sources": ["bcl"],
            "premise": "Rent guarantees at-least length",
            "detail": "exact length needs the exact overload",
        },
        {
            "leaf": "pool clear",
            "state": "refuted",
            "sources": ["folk"],
            "premise": "assumed exact-length",
        },
        {
            "leaf": "memory",
            "state": "folded",
            "into": "rent length",
        },
    ],
    "sweeps": [{"checked": "rival accounts", "candidates": ["folk"], "survivors": []}],
    "checkpoints": [{"label": "round-1", "searches": 4}],
}


@pytest.fixture
def loaded():
    """A ledger with the full batch admitted through the pipeline."""
    ledger = Ledger()
    result = expand_batch(ledger, FULL_BATCH, fixed_mint)
    assert result.problems == []
    return ledger, result


class TestExpansion:
    def test_intra_batch_keyword_reference_is_silent(self, loaded):
        _, result = loaded
        assert result.advisories == []

    def test_every_entry_mints_one_identifier(self, loaded):
        _, result = loaded
        assert sorted(len(group) for group in result.minted.values()) == [2, 3]

    def test_expansion_order_lets_closes_cite_fresh_sources(self, loaded):
        _, result = loaded
        kinds = [event["e"] for event in result.events]
        assert kinds.index("add_source") < kinds.index("close")

    def test_into_carries_the_fold_target(self, loaded):
        _, result = loaded
        fold = next(e for e in result.events if e.get("state") == "folded")
        assert fold["into"].startswith("rent-length-")

    def test_origin_passes_through(self, loaded):
        _, result = loaded
        spawned = [e for e in result.events if e.get("origin") == "spawned"]
        assert len(spawned) == 1

    def test_retrieved_close_keeps_premise_and_detail(self, loaded):
        ledger, _ = loaded
        state = next(
            leaf.state
            for leaf in ledger.leaves.values()
            if isinstance(leaf.state, Retrieved)
        )
        assert state.premise == "Rent guarantees at-least length"
        assert state.detail == "exact length needs the exact overload"


class TestRecovery:
    def test_reference_to_an_older_leaf_records_recovery(self, loaded):
        ledger, _ = loaded
        batch = {
            "sources": [
                {
                    "kw": ["extra", "doc"],
                    "leaf": "rent",
                    "cls": "reported",
                    "title": "t",
                }
            ]
        }
        result = expand_batch(ledger, batch, fixed_mint)
        assert any(
            line.startswith("recovered leaf 'rent'") for line in result.advisories
        )

    def test_ambiguous_reference_lists_the_candidates(self, loaded):
        ledger, _ = loaded
        batch = {
            "sources": [
                {"kw": ["x", "y"], "leaf": "pool", "cls": "reported", "title": "t"}
            ]
        }
        result = expand_batch(ledger, batch, fixed_mint)
        [problem] = result.problems
        assert "matches several" in problem.fix
        assert "write one of:" in problem.hint

    def test_an_unknown_reference_gets_a_did_you_mean(self, loaded):
        ledger, _ = loaded
        batch = {
            "closes": [
                {"leaf": "rent length", "state": "retrieved", "sources": ["gile"]}
            ]
        }
        result = expand_batch(ledger, batch, fixed_mint)
        [problem] = result.problems
        assert problem.where == "closes[0].sources[0]"
        assert "no source matches" in problem.fix

    def test_near_misses_rank_by_keyword_overlap(self):
        ids = ["rds-assessment-abc", "rds-methods-def", "other-topic-ghi"]
        assert suggest("rds assessment", ids)[0] == "rds-assessment-abc"


class TestTotalRejection:
    def test_two_independent_problems_arrive_in_one_verdict(self, loaded):
        """The friction this redesign exists to kill: serial discovery."""
        ledger, _ = loaded
        batch = {
            "closes": [
                {"leaf": "rent length", "state": "retrieved", "sources": ["gile"]}
            ],
            "sweeps": [
                {
                    "checked": "x",
                    "candidates": ["a claim"],
                    "survivors": ["a claim, qualified"],
                }
            ],
        }
        result = expand_batch(ledger, batch, fixed_mint)
        wheres = {problem.where for problem in result.problems}
        assert "closes[0].sources[0]" in wheres
        assert "sweeps[0].survivors[0]" in wheres

    def test_a_rejected_batch_stages_no_event_for_the_broken_entry(self, loaded):
        ledger, _ = loaded
        batch = {"closes": [{"leaf": "nope nope", "state": "retrieved"}]}
        result = expand_batch(ledger, batch, fixed_mint)
        assert result.events == []
        assert result.problems

    def test_vocabulary_violations_carry_the_schema_fragment(self):
        batch = {"leaves": [{"kw": ["a", "b"], "q": "x", "origin": "invented"}]}
        result = expand_batch(Ledger(), batch, fixed_mint)
        [problem] = result.problems
        # The field type names the vocabulary; the hint keeps the schema
        # fragment, which is where the whole entry shape is spelled out.
        assert "'frame'" in problem.fix
        assert "frame|spawned" in problem.hint

    def test_empty_batch_is_a_problem_not_a_crash(self):
        result = expand_batch(Ledger(), {}, fixed_mint)
        assert any("records nothing" in p.fix for p in result.problems)

    def test_unknown_top_level_key_names_the_valid_keys(self):
        result = expand_batch(Ledger(), {"leafs": []}, fixed_mint)
        assert any("valid keys" in (p.hint or "") for p in result.problems)

    def test_unsluggable_keywords_are_a_located_problem(self):
        result = expand_batch(
            Ledger(), {"leaves": [{"kw": ["!!"], "q": "x"}]}, fixed_mint
        )
        assert any(p.where == "leaves[0].kw[0]" for p in result.problems)

    def test_duplicate_keywords_in_one_batch_are_a_problem(self):
        batch = {"leaves": [{"kw": ["a", "b"], "q": "x"}, {"kw": ["a", "b"], "q": "y"}]}
        result = expand_batch(Ledger(), batch, fixed_mint)
        assert any("vary one keyword" in p.fix for p in result.problems)


class TestSweepSurvivors:
    def test_indexes_resolve_into_candidates(self):
        batch = {
            "sweeps": [
                {"checked": "x", "candidates": ["first", "second"], "survivors": [1]}
            ]
        }
        result = expand_batch(Ledger(), batch, fixed_mint)
        assert result.problems == []
        assert result.events[0]["survivors"] == ["second"]

    def test_an_out_of_range_index_is_a_problem(self):
        batch = {"sweeps": [{"checked": "x", "candidates": ["only"], "survivors": [3]}]}
        result = expand_batch(Ledger(), batch, fixed_mint)
        assert any("out of range" in p.fix for p in result.problems)

    def test_a_verbatim_string_still_works(self):
        batch = {
            "sweeps": [{"checked": "x", "candidates": ["kept"], "survivors": ["kept"]}]
        }
        result = expand_batch(Ledger(), batch, fixed_mint)
        assert result.problems == []


class TestExplicitRefAndMerge:
    def test_an_explicit_ref_names_the_minted_id(self):
        batch = {
            "leaves": [{"kw": ["a", "b"], "q": "x"}],
            "sources": [
                {
                    "ref": "gile-handcock",
                    "kw": ["rds", "assessment"],
                    "leaf": "a b",
                    "cls": "reported",
                    "title": "t",
                }
            ],
        }
        result = expand_batch(Ledger(), batch, fixed_mint)
        assert result.problems == []
        assert "gile-handcock" in result.minted["sources"]

    def test_a_duplicate_url_merges_instead_of_minting(self, loaded):
        ledger, first = loaded
        batch = {
            "leaves": [{"kw": ["new", "leaf"], "q": "x"}],
            "sources": [
                {
                    "kw": ["dupe", "post"],
                    "leaf": "new leaf",
                    "cls": "reported",
                    "title": "same doc",
                    "url": BCL_URL,
                }
            ],
        }
        result = expand_batch(ledger, batch, fixed_mint)
        assert result.problems == []
        assert result.merged == {"dupe-post": first.minted["sources"]["bcl-rent"]}


class TestCheckpoints:
    def test_a_checkpoint_cannot_smuggle_another_event_kind(self):
        """The entry once spread into the event, so `e` could be overwritten
        and a leaf reached the ledger without passing through minting."""
        ledger = Ledger()
        result = expand_batch(
            ledger,
            {"checkpoints": [{"e": "add_leaf", "id": "smuggled", "q": "bypassed"}]},
            fixed_mint,
        )
        assert result.problems
        assert not ledger.leaves

    def test_a_checkpoint_records_its_round(self):
        result = expand_batch(
            Ledger(), {"checkpoints": [{"label": "round-1", "searches": 5}]}, fixed_mint
        )
        assert not result.problems
        assert result.events == [{"e": "checkpoint", "label": "round-1", "searches": 5}]
