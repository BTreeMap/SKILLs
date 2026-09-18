"""require and demand: the decoder's two verbs."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, demand, require


def test_require_raises_the_invariant():
    require(True, "fine")
    with pytest.raises(CommandError, match="broken"):
        require(False, "broken")


def test_demand_narrows_an_optional_or_names_the_invariant():
    assert demand("value", "absent") == "value"
    with pytest.raises(CommandError, match="absent"):
        demand(None, "absent")
