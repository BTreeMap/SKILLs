"""`check --live` on planted real fills: a sleeve following the model
tracks it, a 30% loss trips `drawdown` once a week, an old panel trips
`stale`, and the command writes incident lines and nothing else."""

from __future__ import annotations

import json
import secrets
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from btm_finance.api import Market
from btm_finance.cli import scoped
from btm_finance.data.assemble import assemble
from btm_finance.data.tables import date_of
from btm_finance.ledger import Kind
from btm_finance.live import Fill, Seasoning, Watch, slippage, tier_of
from btm_finance.loader import load_strategy
from btm_finance.measuring import Setting, rebalance_rows, rules_of, target_weights
from btm_finance.models import Rebalance, StrategyConfig
from btm_finance.proposing import Tier
from btm_finance.store import append_ledger, load_limits, load_preferences, open_book

CAPITAL = 1e6


@pytest.fixture
def paper(synthetic, run):
    """Seed 7 with `max_weight` 1 and the participation bound eased (the
    operator's edits), so the baseline's weights sum to 1 like a fully funded
    sleeve; one run; status live."""
    book = synthetic(seed=7)
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["sizing"]["max_weight"] = 1.0
    limits["max_adv_participation"] = 0.05
    path.write_text(json.dumps(limits))
    code, _, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    (book / "strategies" / "baseline" / "status").write_text("live\n")
    return book


def model_fills(book: Path) -> list[dict[str, object]]:
    """Buys at the next open after the baseline's last rebalance, at the
    model's target weights: the trades `measure` itself makes."""
    handle = open_book(str(book))
    folder = book / "strategies" / "baseline"
    config = StrategyConfig.model_validate_json((folder / "config.json").read_text())
    panel, events = assemble(handle)
    names = scoped(handle, panel.names, held_out=False)
    panel, events = panel.only(names), events.only(names)
    rules = rules_of(load_limits(handle), load_preferences(handle), config)
    setting = Setting.of(panel, events, rules)
    strategy = load_strategy(book, "baseline").signal
    row = int(rebalance_rows(panel.dates, Rebalance.ANNUAL)[-1])
    market = Market.at(panel, events, int(panel.dates[row]))
    index = {name: column for column, name in enumerate(panel.names)}
    raw = strategy(market, dict(config.params))
    weights = target_weights(raw, market, setting, index, row).weights
    assert abs(weights.sum() - 1.0) < 1e-9
    day = date_of(int(panel.dates[row + 1])).isoformat()
    return [
        {
            "symbol": panel.names[column],
            "side": "buy",
            "quantity": float(weights[column] * CAPITAL / panel.open[row + 1, column]),
            "price": float(panel.open[row + 1, column]),
            "date": day,
            "strategy": "baseline",
        }
        for column in np.flatnonzero(weights > 0).tolist()
    ]


def record(run, book: Path, fills: list[dict[str, object]]) -> None:
    """Planted fill lines: trades the gate let in under earlier approvals."""
    del run
    rows = [
        {"id": f"fill-{secrets.token_hex(4)}", "ts": "2000-01-03T00:00:00Z"} | fill
        for fill in fills
    ]
    append_ledger(open_book(str(book)).path_of(Kind.FILL), rows)


def live(run, book: Path, today: str) -> dict[str, object]:
    code, document, err = run(["check", str(book), "--live", "--today", today])
    assert code == 0, err
    return document


def last_bar(book: Path) -> date:
    panel, _ = assemble(open_book(str(book)))
    return date_of(int(panel.dates[-1]))


def incidents(book: Path, kind: str) -> list[dict[str, object]]:
    path = book / "ledger" / "incidents.jsonl"
    lines = path.read_text().splitlines() if path.exists() else []
    return [row for row in map(json.loads, lines) if row["kind"] == kind]


def test_a_sleeve_following_the_model_tracks_it(paper, run):
    record(run, paper, model_fills(paper))
    document = live(run, paper, last_bar(paper).isoformat())
    (row,) = document["strategies"]
    assert row["days"] > 100
    assert 0 <= row["tracking"]["value"] < 0.01  # costs alone separate them
    assert not row["tracking"]["breach"]
    assert document["breaches"] == []
    assert len(document["report"].splitlines()) <= 20


def test_a_planted_loss_trips_drawdown_once_a_week(paper, run):
    day = last_bar(paper) - timedelta(days=60)
    panel, _ = assemble(open_book(str(paper)))
    row = int(np.searchsorted(panel.dates, (day - date(1970, 1, 1)).days))
    close = float(panel.close[row, 20])
    loss = {
        "symbol": panel.names[20],
        "side": "buy",
        "quantity": 100.0,
        "price": close / 0.7,  # marked at the close: a 30% loss on day one
        "date": date_of(int(panel.dates[row])).isoformat(),
        "strategy": "baseline",
    }
    record(run, paper, [loss])
    before = {p: p.read_bytes() for p in paper.rglob("*") if p.is_file()}
    today = last_bar(paper).isoformat()
    first = live(run, paper, today)
    assert Watch.DRAWDOWN in {b["kind"] for b in first["breaches"]}
    assert len(incidents(paper, "drawdown")) == 1
    second = live(run, paper, today)
    assert second["new"] == [] and second["repeated"] >= 1
    assert len(incidents(paper, "drawdown")) == 1
    after = {p: p.read_bytes() for p in paper.rglob("*") if p.is_file()}
    changed = {
        p.relative_to(paper).as_posix() for p in after if before.get(p) != after[p]
    }
    assert changed == {"ledger/incidents.jsonl"}


def test_an_old_panel_trips_stale(paper, run):
    fresh_day = live(run, paper, last_bar(paper).isoformat())
    assert not fresh_day["strategies"][0]["stale"]["breach"]
    late = live(run, paper, (last_bar(paper) + timedelta(days=30)).isoformat())
    assert late["strategies"][0]["stale"]["breach"]
    assert [i["strategy"] for i in incidents(paper, "stale")] == ["baseline"]


def test_slippage_is_cost_for_either_side():
    buy = Fill("A", 10.0, 10.1, 0, 10.0)
    sell = Fill("A", -10.0, 9.9, 0, 10.0)
    unknown = Fill("A", 10.0, 50.0, 0, None)
    assert slippage([buy, sell, unknown]) == pytest.approx(0.01)


@pytest.mark.parametrize(
    "named", [{"proposal": "2019-07-31"}, {"approval": "2019-07-31.json"}]
)
def test_slippage_reads_the_proposal_the_fill_names(paper, run, named):
    """Fill, its `proposal` stem (an older fill's `approval` stem), that
    order's price."""
    day = last_bar(paper).isoformat()
    order = {"symbol": "S020", "side": "buy", "quantity": 10, "price": 50.0}
    (paper / "proposals").mkdir(exist_ok=True)
    (paper / "proposals" / "2019-07-31.json").write_text(
        json.dumps({"orders": [order]})
    )
    fill = order | {"price": 50.5, "date": day, "strategy": "baseline"} | named
    record(run, paper, [fill])
    (row,) = live(run, paper, day)["strategies"]
    assert row["slippage"]["value"] == pytest.approx(0.01)


def tier(run, book: Path, day: date) -> str:
    """`check --propose` on `day`, then the baseline sleeve's tier in the
    file."""
    code, _, err = run(["check", str(book), "--propose", day.isoformat()])
    assert code == 0, err
    path = book / "proposals" / f"{day.isoformat()}.json"
    return json.loads(path.read_text())["sleeves"]["baseline"]["tier"]


def first_fill_day(fills: list[dict[str, object]]) -> date:
    return date.fromisoformat(str(fills[0]["date"]))


def test_no_fills_size_on_the_backtest(paper, run):
    assert tier(run, paper, last_bar(paper)) == "backtest"


def test_a_short_span_stays_backtest(paper, run):
    fills = model_fills(paper)
    record(run, paper, fills)
    early = first_fill_day(fills) + timedelta(days=30)
    assert tier(run, paper, early) == "backtest"  # under 63 calendar days


def test_a_long_span_tracking_the_model_is_tracked(paper, run):
    fills = model_fills(paper)
    record(run, paper, fills)
    assert (last_bar(paper) - first_fill_day(fills)).days >= 63
    assert tier(run, paper, last_bar(paper)) == "tracked"


def test_a_long_span_off_the_model_path_stays_backtest(paper, run):
    # The whole capital in one name: realized path far off the model's.
    first = model_fills(paper)[0]
    record(run, paper, [first | {"quantity": CAPITAL / float(str(first["price"]))}])
    report = live(run, paper, last_bar(paper).isoformat())
    assert report["strategies"][0]["tracking"]["breach"]
    assert tier(run, paper, last_bar(paper)) == "backtest"


def test_an_older_probe_with_dry_run_fills_tracks_real_fills_only(paper, run):
    (paper / "strategies" / "baseline" / "status").write_text("probe\n")
    fills = model_fills(paper)
    record(run, paper, [f | {"dry_run": True, "quantity": 1.0} for f in fills[:1]])
    record(run, paper, fills)
    (row,) = live(run, paper, last_bar(paper).isoformat())["strategies"]
    assert (row["strategy"], row["status"]) == ("baseline", "live")
    assert row["fills"] == len(fills)  # the dry-run fill is no trade
    assert row["days"] > 100
    assert not row["tracking"]["breach"]
    assert tier(run, paper, last_bar(paper)) == "tracked"


def test_tier_of_needs_both_span_and_tracking():
    good, short = Seasoning(90, 0.01), Seasoning(10, 0.01)
    off, blind = Seasoning(90, 0.20), Seasoning(90, None)

    def pick(found: Seasoning | None) -> Tier:
        return tier_of(found, days=63, bound=0.05)

    assert pick(None) is Tier.BACKTEST
    assert pick(short) is Tier.BACKTEST
    assert pick(off) is Tier.BACKTEST
    assert pick(blind) is Tier.BACKTEST
    assert pick(good) is Tier.TRACKED
