"""G2: strategy code reaches data only through the data API. Each forbidden
construct in `signal.py` is refused by node before any of it runs, and an
unregistered strategy is refused; neither writes a run line."""

from __future__ import annotations

import pytest
from btm_finance.whitelist import READERS, screen

RETURN = "\n\ndef signal(market, params):\n    return {}\n"
FORBIDDEN = [
    ('data = open("data/manifest.json")\n', 1, "name open"),
    ("import os\n", 1, "import os"),
    ("import pyarrow\n", 1, "import pyarrow"),
    ("from btm_finance.data import raw\n", 1, "from btm_finance.data import raw"),
    ('os = __import__("os")\n', 1, "name __import__"),
    ('read = getattr(object, "mro")\n', 1, "name getattr"),
    ("import numpy\nkind = numpy.__class__\n", 2, "attribute .__class__"),
    ("import btm_finance.api\n", 1, "import btm_finance.api"),
    ("from btm_finance import api\nx = api.on_dates\n", 2, "attribute api.on_dates"),
    ("from btm_finance import api as a\nx = a.FACTORS\n", 2, "attribute a.FACTORS"),
    ("x = btm_finance.data\n", 1, "attribute btm_finance.data"),
    *(
        (f"import numpy as np\nx = np.{name}\n", 2, f"attribute .{name}")
        for name in sorted(READERS)
    ),
]


@pytest.mark.parametrize("case", FORBIDDEN)
def test_each_forbidden_construct_is_refused_by_node(book, run, plant, case):
    code, line, node = case
    plant(book, "probe", code + RETURN)
    exit_code, document, err = run(["measure", str(book), "probe"])
    assert exit_code == 1
    assert document is None
    assert f"strategies/probe/signal.py:{line}: refused {node}" in err
    assert not (book / "ledger" / "runs.jsonl").exists()


def test_every_refusal_comes_back_at_once():
    source = "import os\nimport socket\n\ndef signal(m, p):\n    return eval('1')\n"
    found = [(r.line, r.node) for r in screen(source, "s.py")]
    assert found == [(1, "import os"), (2, "import socket"), (5, "name eval")]


def test_the_two_api_import_forms_and_the_listed_modules_pass():
    source = (
        "from btm_finance import api\n"
        "kind = api.Market\n"
        "from btm_finance.api import Market\n"
        "import numpy as np\n"
        "from collections import deque\n"
        "import math, statistics, itertools, functools, operator, dataclasses, typing\n"
    )
    assert screen(source, "s.py") == []
    assert [r.node for r in screen("from btm_finance.api import on_dates\n", "s")] == [
        "from btm_finance.api import on_dates"
    ]
    assert [r.node for r in screen("from numpy import *\n", "s")] == [
        "from numpy import * (import *)"
    ]


def test_an_unregistered_strategy_is_refused(book, run):
    folder = book / "strategies" / "ghost"
    folder.mkdir()
    (folder / "signal.py").write_text(RETURN)
    code, _, err = run(["measure", str(book), "ghost"])
    assert code == 1
    assert "unregistered" in err
    assert not (book / "ledger" / "runs.jsonl").exists()
