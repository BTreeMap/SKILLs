"""Book hooks under `lib/`: a book source loads through `load`, a `Market`
extension sees research names only and never shadows a core accessor, a
metric lands in `scorecard.extra`, a cost model replaces the default, a
sizing rule is recorded in the proposal, a moved hook refuses a repeat, and
bare `check` lists every hook with its uses."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from textwrap import dedent

import pytest
from btm_finance.data.raw import read_manifest
from btm_finance.ledger import Kind
from btm_finance.store import append_ledger, held_out_list, open_book

PEEK = """\
def extend(market):
    def everyone():
        return tuple(market._bars.names)

    return {"everyone": everyone}
"""
SIGNAL = dedent(
    """\
    import json
    from pathlib import Path

    SEEN = Path(__file__).with_name("seen.json")


    def signal(market, params):
        names = set(market.everyone()) | set(market.names)
        old = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()
        SEEN.write_text(json.dumps(sorted(old | names)))
        return {name: 1.0 for name in market.names[:10]}
    """
)
PLAIN = dedent(
    """\
    def signal(market, params):
        return {name: 1.0 for name in market.names[:10]}
    """
)
HITS = """\
def metric(returns, positions, market):
    shape = (len(returns), len(positions.names))
    if positions.weights.shape != shape or not market.names:
        return -1.0
    return float(len(returns))
"""
FREE = """\
def cost(trade, market):
    return 0.0 if trade.notional and market.names else 1.0
"""


def hook(book: Path, relative: str, source: str) -> Path:
    path = book / "lib" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return path


def measured(run, book: Path, name: str) -> dict:
    code, receipt, err = run(["measure", str(book), name])
    assert code == 0, err
    return receipt


def run_line(book: Path) -> dict:
    return json.loads((book / "ledger" / "runs.jsonl").read_text().splitlines()[-1])


def test_a_market_extension_sees_research_names_only(synthetic, run, plant):
    book = synthetic(seed=7)
    hook(book, "market/peek.py", PEEK)
    plant(book, "peek", SIGNAL)
    measured(run, book, "peek")
    seen = set(json.loads((book / "strategies" / "peek" / "seen.json").read_text()))
    hidden = held_out_list(open_book(str(book)))
    assert seen and hidden
    assert not seen & hidden
    assert set(run_line(book)["extensions"]) == {"market/peek"}


def test_a_market_extension_cannot_shadow_a_core_accessor(synthetic, run, plant):
    book = synthetic(seed=7)
    hook(book, "market/bad.py", "def extend(market):\n    return {'close': len}\n")
    plant(book, "plain", PLAIN)
    code, _, err = run(["measure", str(book), "plain"])
    assert code == 1
    assert "close shadows a core Market accessor" in err


def test_a_metric_and_a_cost_model_land_on_the_run_line(synthetic, run, plant):
    book = synthetic(seed=7)
    hook(book, "metrics/hits.py", HITS)
    hook(book, "costs.py", FREE)
    plant(book, "plain", PLAIN)
    card = measured(run, book, "plain")["scorecard"]
    line = run_line(book)
    assert card["extra"] == {"hits": float(line["span"]["periods"])}
    assert card["cost_share"] == pytest.approx(0.0, abs=1e-12)
    levels = card["capacity"]
    assert levels["0.1x"] == pytest.approx(levels["20x"])
    assert line["costs"] == "lib/costs.py"
    assert set(line["extensions"]) == {"metrics/hits", "costs/costs"}


def test_repeat_refuses_a_moved_or_vanished_extension(synthetic, run, plant):
    book = synthetic(seed=7)
    path = hook(book, "metrics/hits.py", HITS)
    plant(book, "plain", PLAIN)
    run_id = measured(run, book, "plain")["run_id"]
    repeat = ["measure", str(book), "plain", "--repeat", run_id]
    path.write_text(HITS + "\n# a comment moves nothing\n")
    code, _, err = run(repeat)
    assert code == 0, err
    path.write_text(HITS.replace("float(len(returns))", "2.0"))
    code, _, err = run(repeat)
    assert code == 1
    assert "extension metrics/hits moved" in err
    path.unlink()
    code, _, err = run(repeat)
    assert code == 1
    assert "extension metrics/hits vanished" in err


SOURCE = """\
from btm_finance.data.tables import Loaded, bars_from


def fetch(since, config):
    prices = {key: [config["close"]] for key in ("open", "high", "low", "close")}
    prices["volume"] = [1000.0]
    bars = bars_from(["ZZZ"], [since.isoformat()], prices, ["nyse"], "mine")
    return Loaded(bars, None)
"""


def test_a_book_source_loads_through_load(book, run, tmp_path):
    hook(book, "sources/mine.py", SOURCE)
    config = tmp_path / "mine.json"
    config.write_text(json.dumps({"close": 12.5}))
    argv = ["load", str(book), "mine", "--since", "2024-01-02"]
    code, receipt, err = run([*argv, "--config:file", str(config)])
    assert code == 0, err
    assert receipt["rows"] == {"bars": 1, "events": 0, "posts": 0}
    (entry,) = read_manifest(open_book(str(book))).files
    assert (entry.source, entry.path.split("/")[:3]) == (
        "mine",
        ["data", "raw", "mine"],
    )
    view = run(["check", str(book)])[1]
    [row] = view["extensions"]
    assert (row["hook"], row["name"], row["runs"]) == ("sources", "mine", 1)
    code, _, err = run(["load", str(book), "nosuch"])
    assert code == 1
    assert "lib/sources/nosuch.py" in err


SIZING = """\
def weights(sleeves, limits):
    return {name: 0.03 + 0.0 * sleeve["kelly"] for name, sleeve in sleeves.items()}
"""
DAY = "2016-12-30"


def test_a_sizing_rule_shadows_kelly_and_the_proposal_records_it(synthetic, run):
    book = synthetic(seed=7)
    (book / "strategies" / "baseline" / "status").write_text("live\n")
    measured(run, book, "baseline")
    fill = {
        "id": "fill-planted",
        "ts": "2016-01-04T00:00:00Z",
        "symbol": "S001",
        "side": "buy",
        "quantity": 10,
        "price": 10.0,
        "date": "2016-01-04",
        "strategy": "baseline",
        "proposal": "2016-01-04",
    }
    append_ledger(open_book(str(book)).path_of(Kind.FILL), [fill])
    hook(book, "sizing.py", SIZING)
    hook(book, "brief.py", "def lines(book):\n    return []\n")
    code, receipt, err = run(["check", str(book), "--propose", DAY])
    assert code == 0, err
    document = json.loads((book / "proposals" / f"{DAY}.json").read_text())
    assert (receipt["sizing"], document["sizing"]) == ("lib/sizing.py",) * 2
    assert set(document["extensions"]) == {"sizing/sizing", "brief/brief"}
    sleeve = document["sleeves"]["baseline"]
    assert sleeve["weight"] == pytest.approx(0.03)
    assert sleeve["adv_participation"] > 0
    hook(book, "sizing.py", "def weights(sleeves, limits):\n    return {'x': 1}\n")
    code, _, err = run(["check", str(book), "--propose", DAY, "--force"])
    assert code == 1
    assert "name a sleeve" in err


def test_check_lists_hooks_with_uses_and_idle(synthetic, run, plant):
    book = synthetic(seed=7)
    hook(book, "metrics/hits.py", HITS)
    hook(
        book,
        "metrics/spare.py",
        "def metric(returns, positions, market):\n    return None\n",
    )
    plant(book, "plain", PLAIN)
    measured(run, book, "plain")
    rows = {row["name"]: row for row in run(["check", str(book)])[1]["extensions"]}
    today = date.today().isoformat()
    assert rows["hits"]["runs"] == rows["spare"]["runs"] == 1
    assert rows["hits"]["last"][:10] <= today
    assert rows["hits"]["idle"] is False
    hook(book, "metrics/later.py", HITS)
    rows = {row["name"]: row for row in run(["check", str(book)])[1]["extensions"]}
    assert (rows["later"]["runs"], rows["later"]["idle"]) == (0, True)
