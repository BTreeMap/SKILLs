"""The skill's reference scorecard: the baseline strategy on a seeded synthetic
book, pinned field by field within `limits.repeat_tolerance`.

Moving this pin is a method change: a `measure`, cost, data API, or synthetic
generator edit that shifts any number here needs a pull request whose notes
say which field moved and why. Regenerate only then, with
`BTM_FINANCE_REPIN=1`, and commit the new `reference/baseline.json`.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

PIN = Path(__file__).parent / "reference" / "baseline.json"
SEED, NAMES, DAYS = 11, 60, 1200
TOLERANCE = 1e-4  # limits.repeat_tolerance in the template


def differences(pinned: Any, found: Any, where: str = "scorecard") -> list[str]:
    """Every field that differs: numbers beyond tolerance, relative above 1."""
    if isinstance(pinned, dict) and isinstance(found, dict):
        keys = sorted(set(pinned) | set(found))
        return [
            problem
            for key in keys
            for problem in differences(
                pinned.get(key), found.get(key), f"{where}.{key}"
            )
        ]
    if (
        isinstance(pinned, list)
        and isinstance(found, list)
        and len(pinned) == len(found)
    ):
        return [
            problem
            for i, (a, b) in enumerate(zip(pinned, found, strict=True))
            for problem in differences(a, b, f"{where}[{i}]")
        ]
    numbers = (int, float)
    if isinstance(pinned, numbers) and isinstance(found, numbers):
        if math.isclose(pinned, found, rel_tol=TOLERANCE, abs_tol=TOLERANCE):
            return []
    elif pinned == found:
        return []
    return [f"{where}: pinned {pinned!r}, found {found!r}"]


def test_the_baseline_scorecard_matches_the_pin(synthetic, run):
    book = synthetic(seed=SEED, names=NAMES, days=DAYS)
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    card = document["scorecard"]
    if os.environ.get("BTM_FINANCE_REPIN") == "1":
        PIN.parent.mkdir(exist_ok=True)
        PIN.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n")
    pinned = json.loads(PIN.read_text())
    assert differences(pinned, card) == []


def test_the_comparison_names_a_moved_field():
    assert differences({"a": 1.0, "b": [1, 2]}, {"a": 1.00001, "b": [1, 2]}) == []
    assert differences({"a": 1.0}, {"a": 1.01}) == [
        "scorecard.a: pinned 1.0, found 1.01"
    ]
    assert differences({"a": None}, {"a": 0.0}) == [
        "scorecard.a: pinned None, found 0.0"
    ]
