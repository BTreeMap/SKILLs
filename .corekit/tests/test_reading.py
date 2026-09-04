"""The replay boundary: one narrowing per field, and every refusal reaches the
command channel rather than escaping as a TypeError deep in a view."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError
from btm_corekit.reading import read_count, read_opt_text, read_text, read_texts


@pytest.mark.parametrize(
    ("read", "raw", "message"),
    [
        (read_text, {"k": "  "}, "needs a non-empty k"),
        (read_text, {"k": 7}, "needs a non-empty k"),
        (read_opt_text, {"k": 7}, "k must be text"),
        (read_texts, {"k": ["a", 2]}, "k must be a list of strings"),
        (read_texts, {"k": "not a list"}, "k must be a list of strings"),
        (read_count, {"k": -1}, "integer of at least 0"),
        (read_count, {"k": True}, "integer of at least 0"),
        (read_count, {}, "integer of at least 0"),
    ],
)
def test_a_corrupt_field_is_refused_by_name(read, raw, message):
    with pytest.raises(CommandError, match=message):
        read(raw, "k", "the record")


def test_an_absent_optional_field_is_absence_not_failure():
    assert read_opt_text({}, "k", "the record") is None


def test_a_bool_is_never_a_count():
    """`True` is an int in Python, so a JSON `true` would otherwise pass as 1
    and silently become a page number."""
    with pytest.raises(CommandError):
        read_count({"k": True}, "k", "the record")
