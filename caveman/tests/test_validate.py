"""Structural equality: what a compression may change, and what it may not."""

from __future__ import annotations

from btm_caveman.model import Verdict
from btm_caveman.validate import validate


class TestVerdict:
    def test_an_empty_verdict_is_valid(self):
        assert Verdict().is_valid

    def test_an_error_invalidates(self):
        assert not Verdict(errors=("a",)).is_valid

    def test_a_warning_does_not_invalidate(self):
        assert Verdict(warnings=("w",)).is_valid


class TestValidate:
    def test_shortening_prose_is_allowed(self):
        assert validate(
            "# H\nsome long prose here\n`k`\n", "# H\nprose\n`k`\n"
        ).is_valid

    def test_sentence_punctuation_after_a_url_is_prose(self):
        moved = validate(
            "See https://a.example/d and more\n", "See https://a.example/d.\n"
        )
        assert moved.is_valid

    def test_a_dropped_url_and_code_block_are_two_errors(self):
        bad = validate("# H\ntext https://a.example\n```\nc\n```\n", "# H\ntext\n")
        assert not bad.is_valid
        assert len(bad.errors) == 2

    def test_a_dropped_indented_code_block_is_an_error(self):
        assert not validate("text\n\n    code line\n", "text\n").is_valid

    def test_a_dropped_heading_is_an_error(self):
        assert not validate("# Kept\n## Dropped\nbody\n", "# Kept\nbody\n").is_valid

    def test_an_identical_document_validates(self):
        text = "# H\nbody with `code` and https://a.example\n"
        assert validate(text, text).is_valid
