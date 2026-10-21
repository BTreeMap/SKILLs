"""The strategy loader: `signal.py` imports the book's `lib/` and its own
helpers; what it reaches outside the book lands under `imports` on the run
line, walked through every book-local module; nothing is refused."""

from __future__ import annotations

import json
from pathlib import Path

from btm_finance.loader import Roots, imports_of, load_strategy

SIGNAL = """import json
import numpy as np
import lib.sizing
from helpers import tilt
from btm_finance import api
from btm_finance.data import raw

KIND = api.Market
""" + (
    "\n\ndef signal(market, params):\n"
    "    return {name: tilt(lib.sizing.unit()) for name in market.names[:10]}\n"
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_measure_lists_imports_from_outside_the_book(synthetic, run, plant):
    book = synthetic(seed=7)
    write(
        book / "lib" / "sizing.py", "import pyarrow\n\n\ndef unit():\n    return 1.0\n"
    )
    plant(book, "probe", SIGNAL, rebalance="quarterly", holding_days=63)
    write(
        book / "strategies" / "probe" / "helpers.py",
        "import pydantic\nfrom lib import sizing\n\n\ndef tilt(x):\n    return x\n",
    )
    code, receipt, err = run(["measure", str(book), "probe"])
    assert receipt is not None, err
    assert receipt["imports"] == ["btm_finance.data", "pyarrow", "pydantic"]
    line = json.loads((book / "ledger" / "runs.jsonl").read_text().splitlines()[-1])
    assert line["imports"] == ["btm_finance.data", "pyarrow", "pydantic"]
    assert "from outside the book" in err
    del code  # bounds may refuse the run; the line is written either way


def test_the_baseline_imports_nothing_from_outside(synthetic, run):
    book = synthetic(seed=7)
    code, receipt, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    assert receipt["imports"] == []


def test_relative_imports_and_api_reach_are_walked(tmp_path):
    folder = tmp_path / "strategies" / "s"
    write(tmp_path / "lib" / "__init__.py", "")
    write(tmp_path / "lib" / "a.py", "from .b import f\n")
    write(tmp_path / "lib" / "b.py", "import httpx\n\n\ndef f():\n    return 1\n")
    write(
        folder / "signal.py",
        "from lib.a import f\nfrom btm_finance import api as A\nimport btm_finance\n"
        "rows = A.ledger\nkind = A.Market\n",
    )
    found = imports_of(folder / "signal.py", Roots(tmp_path, folder))
    assert found == ("btm_finance", "btm_finance.api.ledger", "httpx")


def test_two_strategies_each_load_their_own_helper(tmp_path):
    for name, value in (("one", 1.0), ("two", 2.0)):
        folder = tmp_path / "strategies" / name
        write(folder / "helpers.py", f"VALUE = {value}\n")
        write(
            folder / "signal.py",
            "from helpers import VALUE\n\n\ndef signal(market, params):\n"
            "    return {'A': VALUE}\n",
        )
    first = load_strategy(tmp_path, "one").signal
    second = load_strategy(tmp_path, "two").signal
    assert (first(None, {}), second(None, {})) == ({"A": 1.0}, {"A": 2.0})
