"""Protected regions: frontmatter, fences, headings, indented code, inline spans."""

from __future__ import annotations

from collections import Counter

import pytest

from btm_caveman.markdown import (
    extract_headings,
    extract_inline_codes,
    partition_fences,
    partition_indented,
    split_frontmatter,
)


class TestSplitFrontmatter:
    def test_frontmatter_is_separated_from_the_body(self):
        assert split_frontmatter("---\na: 1\n---\nBody\n") == (
            "---\na: 1\n---\n",
            "Body\n",
        )

    def test_a_document_without_frontmatter_is_all_body(self):
        assert split_frontmatter("No frontmatter") == ("", "No frontmatter")

    @pytest.mark.parametrize(
        "text", ["---\na: 1\n---\nBody\n", "No frontmatter", "", "---\nunclosed\n"]
    )
    def test_the_two_halves_always_rejoin(self, text):
        """The partition law: nothing is lost or duplicated at the split."""
        assert "".join(split_frontmatter(text)) == text


class TestFences:
    TEXT = "prose\n```py\ncode\n```\ntail `x` and `x`\n~~~\nunclosed\n"

    def test_a_closed_fence_becomes_a_protected_block(self):
        assert partition_fences(self.TEXT)[0] == ("```py\ncode\n```",)

    def test_fenced_content_leaves_the_prose(self):
        assert "code" not in partition_fences(self.TEXT)[1]

    def test_an_unclosed_fence_stays_prose(self):
        assert "unclosed" in partition_fences(self.TEXT)[1]

    def test_a_longer_fence_may_contain_a_shorter_one(self):
        nested = "````md\n```\ninner\n```\n````\n"
        assert partition_fences(nested)[0] == ("````md\n```\ninner\n```\n````",)

    def test_inline_spans_are_counted_with_multiplicity(self):
        assert extract_inline_codes(self.TEXT) == Counter({"x": 2})


class TestHeadings:
    def test_a_hash_inside_a_fence_is_not_a_heading(self):
        assert extract_headings("# Real\n```sh\n# comment\n```\n") == (("#", "Real"),)

    def test_an_empty_atx_heading_does_not_swallow_the_next_line(self):
        assert extract_headings("#\nNot a title\n") == (("#", ""),)

    def test_up_to_three_spaces_of_indent_still_heads(self):
        assert extract_headings("   ## Indented\n") == (("##", "Indented"),)

    def test_setext_underlines_are_headings(self):
        assert extract_headings("Title\n====\nSub\n---\n") == (
            ("=", "Title"),
            ("-", "Sub"),
        )

    def test_a_thematic_break_is_not_a_setext_heading(self):
        assert extract_headings("para\n\n----\n") == ()


class TestIndentedCode:
    def test_an_indented_block_after_a_blank_line_is_code(self):
        assert partition_indented("para\n\n    code\n    more\n")[0] == (
            "    code\n    more",
        )

    def test_a_list_continuation_is_not_code(self):
        assert partition_indented("- item\n\n    continuation\n")[0] == ()
