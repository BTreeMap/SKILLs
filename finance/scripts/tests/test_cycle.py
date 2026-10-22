"""G7 and G1 end to end: the baseline as a paper sleeve runs recommend, approve,
and `record --approval --dry-run` for two annual rebalances; the second proposal diffs
against the first's dry-run fills. Also the refusals and the two books kept
apart: a real fill never lands in a paper sleeve's position."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest
from btm_finance import cli, git

FIRST, SECOND = "2016-12-30", "2017-12-29"  # the baseline's annual rebalances


def batch(run, book: Path, payload: dict) -> None:
    code, _, err = run(["record", str(book), "--batch:stdin"], json.dumps(payload))
    assert code == 0, err


def paper_book(synthetic, run) -> Path:
    book = synthetic(seed=7)
    (book / "strategies" / "baseline" / "status").write_text("paper\n")
    git.commit(book, ["strategies/baseline/status"], "promote: baseline paper")
    code, _, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    return book


def recommend(run, book: Path, day: str, *extra: str) -> dict:
    code, receipt, err = run(["recommend", str(book), day, *extra])
    assert code == 0, err
    return receipt


def proposal(book: Path, stem: str) -> dict:
    return json.loads((book / "proposals" / f"{stem}.json").read_text())


def fills(book: Path) -> list[dict]:
    path = book / "ledger" / "fills.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


SEND_DAY = [FIRST]  # the UTC day `check` and `record` read approvals on


@pytest.fixture(autouse=True)
def on_send_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "utc_today", lambda: date.fromisoformat(SEND_DAY[0]))


def approve_and_send(run, book: Path, day: str) -> tuple[int, str]:
    """The operator's reply on `day`: the agent writes the template with the
    reply quoted, commits it, records the approve decision naming it, checks
    it, then records the paper orders as dry-run fills."""
    code, view, err = run(["check", str(book), day])
    assert code == 0, err
    target = book / view["approval_path"]
    target.write_text(json.dumps(view["approval_template"] | {"reply": "approve"}))
    git.commit(book, [view["approval_path"]], f"approve: {day}")
    decision = {
        "kw": ["approve", "rebalance"],
        "subject": day,
        "action": "approve",
        "reason": "approve",
        "applied": [view["approval_path"]],
    }
    batch(run, book, {"decisions": [decision]})
    SEND_DAY[0] = day
    code, checked, err = run(["check", str(book), view["approval_path"]])
    assert (code, checked["problems"]) == (0, []), err
    code, _, err = run(
        ["record", str(book), "--approval", view["approval_path"], "--dry-run"]
    )
    return code, err


def positions(rows: list[dict]) -> dict[str, float]:
    held: dict[str, float] = defaultdict(float)
    for row in rows:
        held[row["symbol"]] += row["quantity"] * (1 if row["side"] == "buy" else -1)
    return {symbol: q for symbol, q in held.items() if q}


def targets(document: dict) -> dict[str, int]:
    return {
        name: target["quantity"]["baseline"]
        for name, target in document["targets"].items()
        if target["quantity"]["baseline"]
    }


def test_two_rebalances_advise_approve_and_dry_run(synthetic, run):
    book = paper_book(synthetic, run)
    recommend(run, book, FIRST)
    first = proposal(book, FIRST)
    assert first["orders"], "the baseline sleeve proposes trades"
    view = run(["check", str(book), FIRST])[1]
    assert list(view)[:4] == ["book", "proposal", "blockers", "baseline"]
    assert view["baseline"][0]["strategy"] == "baseline"
    assert view["blockers"]["baseline"]  # no critique yet: shown, not hidden
    template = view["approval_template"]
    assert (template["date"], template["proposal"]) == (FIRST, FIRST)
    assert set(template["orders"][0]) == {
        "symbol",
        "side",
        "quantity",
        "price",
        "adv_participation",
        "strategy",
        "limit",
    }

    code, err = approve_and_send(run, book, FIRST)
    assert code == 0, err
    landed = fills(book)
    assert len(landed) == len(first["orders"])
    assert {(f["dry_run"], f["strategy"], f["date"]) for f in landed} == {
        (True, "baseline", FIRST)
    }
    assert positions(landed) == targets(first)

    recommend(run, book, SECOND)
    second = proposal(book, SECOND)
    held = positions(landed)
    kept = set(held) & set(targets(second))
    assert kept, "some name stays in the sleeve across the two rebalances"
    for order in second["orders"]:
        assert order["held"] == held.get(order["symbol"], 0.0)
        sign = 1 if order["side"] == "buy" else -1
        assert order["held"] + sign * order["quantity"] == order["target"]
    assert not second["carried"]  # every first order filled

    code, err = approve_and_send(run, book, SECOND)
    assert code == 0, err
    assert positions(fills(book)) == targets(second)


def test_no_sleeve_exits_1_naming_the_reason(synthetic, run):
    book = synthetic(seed=7)
    code, _, err = run(["recommend", str(book), FIRST])
    assert code == 1
    assert "no sleeve" in err
    (book / "strategies" / "baseline" / "status").write_text("paper\n")
    code, _, err = run(["recommend", str(book), FIRST])
    assert code == 1
    assert "skipped baseline" in err
    assert not (book / "proposals" / f"{FIRST}.json").exists()


def test_a_proposal_is_written_once_and_check_needs_one(synthetic, run):
    book = paper_book(synthetic, run)
    code, _, err = run(["check", str(book), FIRST])
    assert code == 1
    assert "no proposal" in err
    recommend(run, book, FIRST)
    code, _, err = run(["recommend", str(book), FIRST])
    assert code == 1
    assert "--force" in err
    assert (
        recommend(run, book, FIRST, "--force")["proposal"]
        == f"proposals/{FIRST}.2.json"
    )
    assert run(["check", str(book), FIRST])[1]["proposal"].endswith(".2.json")


def test_a_real_fill_never_lands_in_a_paper_position(synthetic, run):
    book = paper_book(synthetic, run)
    recommend(run, book, FIRST)
    symbol = proposal(book, FIRST)["orders"][0]["symbol"]
    real = {
        "symbol": symbol,
        "side": "buy",
        "quantity": 100,
        "price": 10.0,
        "date": FIRST,
        "strategy": "baseline",
        "dry_run": False,
    }
    opening = {"date": FIRST, "positions": [{"symbol": "ZZZ", "quantity": 5}]}
    batch(run, book, {"fills": [real], "holdings": [opening]})
    recommend(run, book, FIRST, "--force")
    again = proposal(book, f"{FIRST}.2")
    order = next(o for o in again["orders"] if o["symbol"] == symbol)
    assert (order["held"], order["account"]) == (0.0, "paper")
    assert [(h["symbol"], h["account"]) for h in again["unmanaged"]] == [
        ("ZZZ", "live")
    ]


def test_an_order_over_the_adv_bound_is_cut_and_reported(synthetic, run):
    """Targets already sit inside the ADV bound; a sale of shares held from
    a looser bound is what passes it."""
    book = paper_book(synthetic, run)
    recommend(run, book, FIRST)
    assert approve_and_send(run, book, FIRST)[0] == 0
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["max_adv_participation"] = 0.001  # the operator's word, applied
    path.write_text(json.dumps(limits))
    recommend(run, book, SECOND)
    document = proposal(book, SECOND)
    assert document["cuts"]
    for cut in document["cuts"]:
        assert cut["kept"] < cut["wanted"]
        assert cut["adv_participation"] > cut["bound"] == 0.001
    assert all(o["adv_participation"] <= 0.001 for o in document["orders"])
    view = run(["check", str(book), SECOND])[1]
    assert view["cuts"] == document["cuts"]


@pytest.mark.parametrize("rejected", [False, True])
def test_an_unfilled_order_carries_once(synthetic, run, rejected):
    book = paper_book(synthetic, run)
    recommend(run, book, FIRST)
    if rejected:
        reject = {
            "kw": ["skip", "first"],
            "subject": FIRST,
            "action": "reject",
            "reason": "operator skipped the day",
        }
        batch(run, book, {"decisions": [reject]})
    recommend(run, book, SECOND)
    second = proposal(book, SECOND)
    keys = [(o["symbol"], o["strategy"]) for o in second["orders"]]
    assert len(keys) == len(set(keys))
    marked = {o["symbol"] for o in second["orders"] if o["carried_from"]}
    if rejected:
        assert (marked, second["carried"]) == (set(), [])
        return
    first = {o["symbol"] for o in proposal(book, FIRST)["orders"]}
    assert marked == first & {o["symbol"] for o in second["orders"]}
    assert marked, "a name stays wanted, so its unfilled buy carries"
    assert {c["symbol"] for c in second["carried"]} == first
    assert {c["symbol"] for c in second["carried"] if c["merged"]} == marked
