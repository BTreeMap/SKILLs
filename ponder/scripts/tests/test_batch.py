"""The note smart constructor: minting, intra-batch reference, recovery, refusal."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from btm_corekit import CommandError, slugify
from btm_ponder.batch import expand_batch
from btm_ponder.ledger import apply
from btm_ponder.state import Ledger


def fixed_mint(words: Iterable[str]) -> str:
    """Deterministic stand-in for mint, so expansion is assertable."""
    return slugify(words) + "-0123456789abcdefghijklmnop"[:32]


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
        },
        {
            "kw": ["blog", "folk"],
            "leaf": "clear",
            "cls": "reported",
            "title": "folk belief post",
        },
    ],
    "closes": [
        {"leaf": "rent length", "state": "retrieved", "sources": ["bcl"]},
        {
            "leaf": "pool clear",
            "state": "refuted",
            "sources": ["folk"],
            "premise": "assumed exact-length",
        },
        {
            "leaf": "memory",
            "state": "retired",
            "reason": "folded",
            "into": "rent length",
        },
    ],
    "sweeps": [{"checked": "rival accounts", "candidates": ["folk"], "survivors": []}],
    "checkpoints": [{"label": "round-1", "searches": 4}],
}


@pytest.fixture
def loaded():
    """A ledger with the full batch applied, as the selftest built it."""
    ledger = Ledger()
    events, minted, advisories = expand_batch(ledger, FULL_BATCH, fixed_mint)
    for event in events:
        apply(ledger, event)
    return ledger, events, minted, advisories


class TestExpansion:
    def test_intra_batch_keyword_reference_is_silent(self, loaded):
        _, _, _, advisories = loaded
        assert advisories == []

    def test_every_entry_mints_one_identifier(self, loaded):
        _, _, minted, _ = loaded
        assert sorted(len(group) for group in minted.values()) == [2, 3]

    def test_expansion_order_lets_closes_cite_fresh_sources(self, loaded):
        _, events, _, _ = loaded
        kinds = [event["e"] for event in events]
        assert kinds.index("add_source") < kinds.index("close")

    def test_into_carries_the_fold_target(self, loaded):
        _, events, _, _ = loaded
        fold = next(e for e in events if e.get("reason") == "folded")
        assert fold["detail"].startswith("rent-length-")

    def test_origin_passes_through(self, loaded):
        _, events, _, _ = loaded
        spawned = [e for e in events if e.get("origin") == "spawned"]
        assert len(spawned) == 1


class TestRecovery:
    def test_reference_to_an_older_leaf_records_recovery(self, loaded):
        ledger, _, _, _ = loaded
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
        _, _, advisories = expand_batch(ledger, batch, fixed_mint)
        assert any(line.startswith("recovered leaf 'rent'") for line in advisories)

    def test_ambiguous_reference_is_refused(self, loaded):
        ledger, _, _, _ = loaded
        batch = {
            "sources": [
                {"kw": ["x", "y"], "leaf": "pool", "cls": "reported", "title": "t"}
            ]
        }
        with pytest.raises(CommandError, match="ambiguous"):
            expand_batch(ledger, batch, fixed_mint)


class TestRefusals:
    def test_empty_batch_is_refused(self):
        with pytest.raises(CommandError, match="empty note"):
            expand_batch(Ledger(), {}, fixed_mint)

    def test_unknown_top_level_key_is_refused(self):
        with pytest.raises(CommandError, match="unknown note keys"):
            expand_batch(Ledger(), {"leafs": []}, fixed_mint)

    def test_unsluggable_keywords_are_refused(self):
        with pytest.raises(CommandError):
            expand_batch(Ledger(), {"leaves": [{"kw": ["!!"], "q": "x"}]}, fixed_mint)

    def test_duplicate_keywords_in_one_batch_are_refused(self):
        batch = {"leaves": [{"kw": ["a", "b"], "q": "x"}, {"kw": ["a", "b"], "q": "y"}]}
        with pytest.raises(CommandError, match="duplicate keywords in one batch"):
            expand_batch(Ledger(), batch, fixed_mint)

    def test_the_same_stem_may_repeat_across_kinds(self):
        """leaves and sources mint into separate namespaces."""
        batch = {
            "leaves": [{"kw": ["a", "b"], "q": "x"}],
            "sources": [
                {"kw": ["a", "b"], "leaf": "a b", "cls": "reported", "title": "t"}
            ],
        }
        events, _, _ = expand_batch(Ledger(), batch, fixed_mint)
        assert len(events) == 2

    def test_off_band_keyword_count_advises_without_blocking(self):
        _, _, advisories = expand_batch(
            Ledger(), {"leaves": [{"kw": ["solo"], "q": "x"}]}, fixed_mint
        )
        assert any("two or three keywords" in line for line in advisories)
