"""require and parse_enum: the decoder's two verbs."""

from __future__ import annotations

from enum import StrEnum

import pytest

from btm_corekit import CommandError, parse_enum, require


class Colour(StrEnum):
    RED = "red"


def test_require_raises_the_invariant():
    require(True, "fine")
    with pytest.raises(CommandError, match="broken"):
        require(False, "broken")


def test_parse_enum_names_the_vocabulary():
    assert parse_enum(Colour, "red", "colour") is Colour.RED
    with pytest.raises(CommandError, match="colour outside the vocabulary"):
        parse_enum(Colour, "blue", "colour")
