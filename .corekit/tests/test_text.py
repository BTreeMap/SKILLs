"""Linear parsers: each law checked on empty, plain, and adversarial input."""

from __future__ import annotations

import time

from btm_corekit import (
    ascii_words,
    bracketed,
    collapse_whitespace,
    heading_words,
    is_digits,
    keep_table,
    prefixed_number,
    runs,
    strip_tags,
)


def test_ascii_words_lowers_and_splits_on_anything_else():
    assert ascii_words("Rent-Length_2 (v3)") == ["rent", "length", "2", "v3"]
    assert ascii_words("") == [] and ascii_words("---") == []
    assert ascii_words("ünïcode") == ["n", "code"]


def test_runs_keeps_only_its_table_and_never_spans_non_ascii():
    table = keep_table("abc/")
    assert runs("a/b xc? a\u00fc/c", table) == ["a/b", "c", "a", "/c"]
    assert runs("", table) == []


def test_collapse_and_digits():
    assert collapse_whitespace("  a \n\t b  ") == "a b"
    assert is_digits("012") and not is_digits("") and not is_digits("\uff11\uff12")
    assert prefixed_number("j12", "j") == 12
    assert prefixed_number("j", "j") is None and prefixed_number("x12", "j") is None


def test_bracketed_yields_innermost_contents_in_order():
    assert list(bracketed("see [1] and [[C2]] then [O3")) == ["1", "C2"]
    assert list(bracketed("")) == [] and list(bracketed("[]")) == [""]


def test_bracketed_is_linear_on_nested_openers():
    text = "[" * 200_000 + "]"
    started = time.perf_counter()
    assert list(bracketed(text)) == [""]
    assert time.perf_counter() - started < 0.5


def test_strip_tags_drops_closed_spans_and_keeps_an_unclosed_opener():
    assert strip_tags("<jats:p>Hi <b>x</b></jats:p>") == "Hi x"
    assert strip_tags("a < b") == "a < b"
    text = "<" * 200_000
    started = time.perf_counter()
    assert strip_tags(text) == text
    assert time.perf_counter() - started < 0.5


def test_heading_words_drops_a_section_number():
    assert heading_words("6. Limitations and Future Work") == [
        "limitations",
        "and",
        "future",
        "work",
    ]
    assert heading_words("  3.2 Results") == ["results"]
    assert heading_words("42") == [] and heading_words("") == []
