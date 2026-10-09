"""The reflow laws, then the shapes each block kind must keep."""

from __future__ import annotations

from pathlib import Path

import pytest

from btm_repo_gate.rules.wrap import reflow, rule_wrap
from btm_repo_gate.snapshot import Repo

LONG = "far past the width " * 5
FRONTMATTER = f"---\nname: sample\ndescription: >-\n  A folded scalar {LONG}\n---\n"
BODY = "\n".join(
    [
        "",
        "# Title",
        "",
        "A paragraph whose lines are ragged",
        f"because a sentence was deleted, leaving the edges uneven and {LONG}",
        "",
        f"- A bullet that runs {LONG}",
        "  Its continuation line joins it.",
        "- Short bullet.",
        f"1. A numbered item that runs {LONG}",
        "   Continued.",
        "",
        "| a | b |",
        "| --- | --- |",
        f"| a table row {LONG} |",
        "",
        "```text",
        f"fenced code {LONG}",
        "```",
        "",
        '<instructions for="x">',
        f"  <rule>Markup content is verbatim {LONG}</rule>",
        "",
        "  <rule>Blank lines inside a block do not end it.</rule>",
        "</instructions>",
        "",
        f"> A quote {LONG}",
        "",
        "Hard break line kept as is because it ends with two spaces\x20\x20",
        "next line.",
        "",
        f"    indented code {LONG}",
        "",
        "[ref]: https://example.invalid/a/very/long/url/that/is/never/wrapped/or/joined",
        "",
    ]
)
DOCUMENT = FRONTMATTER + BODY
KEPT = ("#", "|", "<", ">", "```", "    ", "[")


def normalized(text: str) -> str:
    return " ".join(text.split())


def kept_lines(text: str) -> list[str]:
    return [line for line in text.split("\n") if line.lstrip().startswith(KEPT)]


def body_of(text: str) -> str:
    return text.split("---\n", 2)[2]


class TestLaws:
    def test_words_are_preserved(self):
        assert normalized(reflow(DOCUMENT)) == normalized(DOCUMENT)

    def test_verbatim_lines_are_preserved_in_order(self):
        assert kept_lines(reflow(DOCUMENT)) == kept_lines(DOCUMENT)

    def test_reflow_is_idempotent(self):
        once = reflow(DOCUMENT)
        assert reflow(once) == once

    @pytest.mark.parametrize("width", [40, 76, 120])
    def test_no_prose_line_exceeds_the_width(self, width):
        fenced = False
        for line in body_of(reflow(DOCUMENT, width)).split("\n"):
            fenced ^= line.startswith("```")
            kept = fenced or line.startswith("    ") or line.lstrip().startswith(KEPT)
            if line.strip() and not kept and not line.endswith("  "):
                assert len(line) <= width or " " not in line.strip()


class TestShapes:
    def test_frontmatter_is_untouched(self):
        assert reflow(DOCUMENT).startswith(FRONTMATTER)

    def test_a_ragged_paragraph_is_refilled(self):
        assert "lines are ragged because a sentence" in reflow(DOCUMENT)

    def test_a_bullet_gets_a_hanging_indent(self):
        out = reflow(DOCUMENT, 40).split("\n")
        start = next(i for i, line in enumerate(out) if line.startswith("- A bullet"))
        assert out[start + 1].startswith("  ") and not out[start + 1].startswith("  -")

    def test_a_numbered_item_hangs_at_three_columns(self):
        out = reflow(DOCUMENT, 40).split("\n")
        start = next(i for i, line in enumerate(out) if line.startswith("1. "))
        assert out[start + 1].startswith("   ") and out[start + 1][3] != " "

    def test_a_code_span_is_never_split(self):
        text = "word " * 12 + "`Closes #42` tail."
        lines = reflow(text, 60).split("\n")
        assert all("`Closes #42`" in line or "`" not in line for line in lines)

    def test_a_hard_break_line_is_kept(self):
        assert "two spaces  \nnext line." in reflow(DOCUMENT)

    def test_cdata_is_raw_even_when_it_looks_like_prose(self):
        text = "<example>\n<![CDATA[\nplain words " + "x " * 60 + "\n]]>\n</example>\n"
        assert reflow(text) == text

    def test_a_void_tag_does_not_open_a_block(self):
        text = "<br>\n\n" + "word " * 30 + "\n"
        assert reflow(text, 40) != text

    def test_a_placeholder_in_markup_does_not_hold_the_block_open(self):
        # A `<skill-root>` placeholder never closes; counted as a tag, it kept
        # every later line verbatim, so a long nested item passed the gate.
        nested = f"  - A nested item that runs {LONG}"
        text = (
            '<commands for="bind">\n'
            'R="uv run --project $(realpath <skill-root>/scripts) tool"\n'
            "</commands>\n\n- Outer item.\n" + nested + "\n"
        )
        out = reflow(text)
        assert nested not in out
        assert all(len(line) <= 76 for line in out.split("\n"))

    def test_a_tag_after_a_cdata_closer_closes_the_block(self):
        text = "<example>\n<![CDATA[\ncode\n]]></example>\n\n" + "word " * 30 + "\n"
        assert reflow(text, 40) != text

    def test_a_same_name_child_keeps_the_block_open(self):
        text = "<a>\n<a>\n</a>\n" + "word " * 30 + "\n</a>\n"
        assert reflow(text, 40) == text


class TestRule:
    def test_only_changed_markdown_is_reported_with_its_repair(self):
        texts = {
            Path("a.md"): DOCUMENT,
            Path("b.md"): "# Tidy\n\nShort.\n",
            Path("c.py"): "x = 1\n",
        }
        findings = list(rule_wrap(Repo(frozenset(), texts, {}, {})))
        assert [f.path for f in findings] == ["a.md"]
        assert findings[0].repair is not None
        assert findings[0].repair.text == reflow(DOCUMENT)
