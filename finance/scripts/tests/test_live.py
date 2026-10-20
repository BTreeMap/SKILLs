"""`check --live` on planted dry-run fills: a sleeve following the model
tracks it, a 30% loss trips `drawdown` once a week, an old panel trips
`stale`, and the command writes incident lines and nothing else."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from btm_finance.api import Market
from btm_finance.cli import scoped
from btm_finance.data.assemble import assemble
from btm_finance.data.tables import date_of
from btm_finance.live import Fill, Sleeve, Watch, months_below, slippage
from btm_finance.models import Rebalance, StrategyConfig
from btm_finance.scoring import Setting, rebalance_rows, rules_of, target_weights
from btm_finance.store import load_limits, load_preferences, open_book
from btm_finance.synthetic import trading_days
from btm_finance.whitelist import load_signal

CAPITAL = 1e6


@pytest.fixture
def paper(synthetic, run):
    """Seed 7 with `max_weight` 1 and the participation bound eased (the
    operator's edits), so the baseline's weights sum to 1 like a fully funded
    sleeve; one run; status paper."""
    book = synthetic(seed=7)
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["sizing"]["max_weight"] = 1.0
    limits["max_adv_participation"] = 0.05
    path.write_text(json.dumps(limits))
    code, _, err = run(["score", str(book), "baseline"])
    assert code == 0, err
    (book / "strategies" / "baseline" / "status").write_text("paper\n")
    return book


def model_fills(book: Path) -> list[dict[str, object]]:
    """Buys at the next open after the baseline's last rebalance, at the
    model's target weights: the trades the scorer itself makes."""
    handle = open_book(str(book))
    folder = book / "strategies" / "baseline"
    config = StrategyConfig.model_validate_json((folder / "config.json").read_text())
    panel, events = assemble(handle)
    names = scoped(handle, panel.names, held_out=False)
    panel, events = panel.only(names), events.only(names)
    rules = rules_of(load_limits(handle), load_preferences(handle), config)
    setting = Setting.of(panel, events, rules)
    strategy = load_signal((folder / "signal.py").read_text(), "signal.py", "t_live")
    row = int(rebalance_rows(panel.dates, Rebalance.ANNUAL)[-1])
    market = Market.at(panel, events, int(panel.dates[row]))
    index = {name: column for column, name in enumerate(panel.names)}
    raw = strategy(market, dict(config.params))
    weights, _ = target_weights(raw, market, setting, index, row)
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
            "dry_run": True,
        }
        for column in np.flatnonzero(weights > 0).tolist()
    ]


def record(run, book: Path, fills: list[dict[str, object]]) -> None:
    code, _, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"fills": fills})
    )
    assert code == 0, err


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
        "dry_run": True,
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


def test_months_below_counts_the_trailing_streak():
    dates = trading_days(400)
    baseline = Sleeve(dates, np.full(len(dates), 0.001), 0, ())
    returns = np.full(len(dates), 0.002)
    returns[-260:] = 0.0  # the last 260 trading days trail the baseline
    behind = months_below(Sleeve(dates, returns, 0, ()), baseline)
    assert 12 <= behind <= 13  # a partly trailing month breaks the streak


def test_slippage_reads_the_proposal_the_approval_names(paper, run):
    """Fill, approval file by name, its `proposal` stem, that order's price."""
    day = last_bar(paper).isoformat()
    order = {"symbol": "S020", "side": "buy", "quantity": 10, "price": 50.0}
    (paper / "proposals").mkdir(exist_ok=True)
    (paper / "proposals" / "2019-07-31.json").write_text(
        json.dumps({"orders": [order]})
    )
    (paper / "approvals").mkdir(exist_ok=True)
    (paper / "approvals" / f"{day}.json").write_text(
        json.dumps({"date": day, "proposal": "2019-07-31", "orders": [order]})
    )
    fill = order | {
        "price": 50.5,
        "date": day,
        "strategy": "baseline",
        "dry_run": True,
        "approval": f"{day}.json",
    }
    record(run, paper, [fill])
    (row,) = live(run, paper, day)["strategies"]
    assert row["slippage"]["value"] == pytest.approx(0.01)
