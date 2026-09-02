"""The page index and anchor resolution."""

from __future__ import annotations

from btm_peer_review.text import Fuzzy, PaperText, Unresolved, Verbatim, parse_pages


class TestPages:
    def test_markers_split_pages_and_keep_numbers(self, paper_text):
        pages = list(paper_text.pages)
        assert [n for n, _ in pages] == [1, 2, 3]
        assert "Experiments" in pages[1][1]

    def test_no_markers_is_one_page(self, paper_text):
        assert parse_pages("just text") == [(1, "just text")]


class TestResolve:
    def test_exact_quote_resolves_to_its_page(self, paper_text):
        found = paper_text.resolve("Baselines were tuned with default hyperparameters")
        assert isinstance(found, Verbatim)
        assert found.page == 2

    def test_curly_quotes_and_line_breaks_still_match(self, paper_text):
        found = paper_text.resolve(
            "improves accuracy by 12 points\nover strong baselines"
        )
        assert isinstance(found, Verbatim)
        assert found.page == 1

    def test_a_small_corruption_resolves_fuzzily(self, paper_text):
        quote = (
            "We report the best run over five seeds. Baselines were tuned with "
            "default hyperparameterz."
        )
        found = paper_text.resolve(quote)
        assert isinstance(found, Fuzzy)
        assert found.page == 2
        assert 0.6 <= found.coverage < 1.0

    def test_invented_text_is_unresolved_with_the_closest_page(self, paper_text):
        found = paper_text.resolve(
            "We report the median over five seeds with error bars"
        )
        assert isinstance(found, Unresolved)
        assert found.coverage < 0.6

    def test_short_absent_text_has_no_page(self, paper_text):
        assert paper_text.resolve("zebra") == Unresolved(None, 0.0)


class TestSections:
    def test_limitations_span_covers_only_that_section(self, paper_text):
        text = paper_text
        inside = text.resolve("Our evaluation covers English only")
        outside = text.resolve("We report the best run over five seeds")
        after = text.resolve("[1] Someone 2020")
        assert text.in_limitations(inside.offset)
        assert not text.in_limitations(outside.offset)
        assert not text.in_limitations(after.offset)

    def test_author_block_is_flagged_from_an_email(self, paper_text):
        assert paper_text.author_block()
        assert not PaperText([(1, "no contact here")]).author_block()

    def test_missing_heading_yields_no_span(self, paper_text):
        assert PaperText([(1, "body only")]).limitations is None
