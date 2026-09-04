"""Laws of the identifier algebra: slugging, minting, resolution, elimination."""

from __future__ import annotations

import pytest

from btm_corekit import (
    Ambiguous,
    CommandError,
    Exact,
    NoMatch,
    Recovered,
    band_signal,
    eliminate,
    keywords_of,
    mint,
    resolve,
    slugify,
    suffix,
)


class TestKeywords:
    def test_splits_on_every_non_slug_run(self):
        assert keywords_of("Rent  Length_v2") == ["rent", "length", "v2"]

    def test_empty_text_yields_no_keywords(self):
        assert keywords_of("") == []
        assert keywords_of("---") == []

    def test_slugify_joins_and_lowercases(self):
        assert slugify(["Rent", "Length"]) == "rent-length"

    def test_slugify_flattens_multi_word_entries(self):
        assert slugify(["rent length", "v2"]) == "rent-length-v2"

    def test_slugify_rejects_content_free_keywords(self):
        with pytest.raises(CommandError):
            slugify(["---", "  "])


class TestBandSignal:
    @pytest.mark.parametrize("stem", ["rent-length", "rent-length-v2"])
    def test_inside_the_band_is_silent(self, stem):
        assert band_signal(stem) is None

    @pytest.mark.parametrize("stem", ["rent", "a-b-c-d"])
    def test_outside_the_band_advises(self, stem):
        signal = band_signal(stem)
        assert signal is not None and stem in signal


class TestResolve:
    IDS = ("rent-length-aaa", "rent-width-bbb", "tax-base-ccc")

    def test_exact_id_wins_over_keyword_search(self):
        assert resolve("rent-length-aaa", self.IDS) == Exact("rent-length-aaa")

    def test_unique_keyword_subset_recovers(self):
        assert resolve("length", self.IDS) == Recovered("rent-length-aaa")

    def test_shared_keyword_is_ambiguous_and_sorted(self):
        assert resolve("rent", self.IDS) == Ambiguous(
            ("rent-length-aaa", "rent-width-bbb")
        )

    def test_a_keyword_never_matches_inside_a_longer_word(self):
        assert resolve("rent", ["current-events-aaa"]) == NoMatch()

    def test_a_keyword_never_matches_the_entropy_suffix(self):
        """The suffix is 26 random base32hex characters, so a one-letter
        keyword lands in better than half of any pool by chance, and in a
        different half on every run. Comparing whole keywords keeps recovery
        deterministic; a substring test made it a coin flip."""
        assert resolve("src b", ["src-a-jl2r20q2l6e9056tl6ckd4hcb4"]) == NoMatch()

    def test_unknown_keyword_matches_nothing(self):
        assert resolve("absent", self.IDS) == NoMatch()

    def test_empty_reference_matches_nothing(self):
        assert resolve("", self.IDS) == NoMatch()

    def test_empty_pool_matches_nothing(self):
        assert resolve("rent", ()) == NoMatch()

    def test_accepts_a_one_shot_iterator(self):
        assert resolve("length", iter(self.IDS)) == Recovered("rent-length-aaa")


class TestEliminate:
    def test_exact_carries_no_signal(self):
        assert eliminate(Exact("rent-length-aaa"), "rent-length-aaa", "session") == (
            "rent-length-aaa",
            None,
        )

    def test_recovered_carries_a_signal_naming_both_forms(self):
        full, signal = eliminate(Recovered("rent-length-aaa"), "length", "session")
        assert full == "rent-length-aaa"
        assert signal is not None
        assert "length" in signal and "rent-length-aaa" in signal

    def test_ambiguous_raises_listing_candidates(self):
        with pytest.raises(CommandError) as caught:
            eliminate(Ambiguous(("a-1", "b-2")), "x", "session")
        assert "a-1" in str(caught.value) and "b-2" in str(caught.value)

    def test_no_match_raises_naming_the_kind(self):
        with pytest.raises(CommandError, match="no session matches"):
            eliminate(NoMatch(), "absent", "session")

    def test_hint_extends_the_no_match_message(self):
        with pytest.raises(CommandError, match="run init first"):
            eliminate(NoMatch(), "absent", "session", "run init first")

    def test_empty_reference_reports_emptiness_over_absence(self):
        with pytest.raises(CommandError, match="empty session reference"):
            eliminate(NoMatch(), "  ", "session")


class TestMinting:
    def test_suffix_is_lowercase_base32hex_without_padding(self):
        value = suffix()
        assert value == value.lower()
        assert "=" not in value
        assert set(value) <= set("0123456789abcdefghijklmnopqrstuv")

    def test_mint_extends_the_slug_with_entropy(self):
        minted = mint(["rent", "length"])
        assert minted.startswith("rent-length-")

    def test_mint_is_collision_free_across_a_batch(self):
        minted = {mint(["rent", "length"]) for _ in range(64)}
        assert len(minted) == 64

    def test_minted_identifier_resolves_exactly(self):
        minted = mint(["rent", "length"])
        assert resolve(minted, [minted]) == Exact(minted)


class TestSharedIndex:
    def test_a_supplied_index_changes_no_verdict(self):
        """resolve and suggest need the same keyword sets; the pool builds
        them once and both read them."""
        ids = ["rent-length-1", "rent-width-2"]
        index = {name: set(keywords_of(name)) for name in ids}
        for ref in ("rent-length-1", "width", "rent", "zzz", ""):
            assert resolve(ref, ids) == resolve(ref, ids, index)
