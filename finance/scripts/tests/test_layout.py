"""The book as research monorepo: what `start` lays out for agent code, book
tests importing `lib`, and the `api` readers a `tools/` script uses."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from btm_finance import api
from btm_finance.data.tables import day_of


def test_start_lays_out_lib_tools_research_tests_and_index(book):
    for folder in ("lib", "tools", "research", "tests"):
        assert (book / folder).is_dir(), folder
    assert (book / "lib" / "__init__.py").read_text() == ""
    index = (book / "INDEX.md").read_text().splitlines()
    assert index == ["# Index", "", "path | purpose"]


def test_book_tests_import_lib(book):
    (book / "lib" / "double.py").write_text("def double(x):\n    return 2 * x\n")
    (book / "tests" / "test_double.py").write_text(
        "from lib.double import double\n\n\ndef test_double():\n"
        "    assert double(2) == 4\n"
    )
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=book,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "1 passed" in done.stdout


def test_api_reads_the_newest_wins_ledger_and_research_names(synthetic, run):
    book = synthetic(seed=7)
    first = {
        "kw": ["first", "read"],
        "subject": "baseline",
        "action": "override",
        "reason": "first",
    }
    code, receipt, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"decisions": [first]})
    )
    assert code == 0, err
    old = receipt["new"]["decisions"]["first-read"]
    fix = first | {"kw": ["second", "read"], "supersedes": old}
    run(["record", str(book), "--batch:stdin"], json.dumps({"decisions": [fix]}))
    code, measured, err = run(["measure", str(book), "baseline", "--agent", "probe"])
    assert code == 0, err

    handle = api.open_book(str(book))
    assert [row["kw"] for row in api.ledger(handle, "decision")] == [["second", "read"]]
    assert [row["run_id"] for row in api.ledger(handle, "run")] == [measured["run_id"]]
    found = api.research(handle)
    market = found.at(date(2100, 1, 1))
    assert market.day == day_of(found.dates[-1])
    hidden = json.loads((book / "book.json").read_text())["held_out"]
    listing = json.loads(Path(hidden).read_text())
    held = {name for names in listing.values() for name in names}
    assert held and not held & set(market.names)
