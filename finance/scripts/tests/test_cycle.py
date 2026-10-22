"""G7 and G1 end to end: the baseline as a live sleeve runs `check
--propose`, an approve decision, and `record --fills:file --proposal` for
two annual rebalances; the second proposal diffs against the first's fills.
Also the refusals, a fill no approval covers, and an older book's dry-run
fills kept out of every position."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest
from btm_finance import cli
from btm_finance.ledger import Kind
from btm_finance.store import append_ledger, open_book

FIRST, SECOND = "2016-12-30", "2017-12-29"  # the baseline's annual rebalances
BOUND = 1e-5  # an ADV bound the first fills already pass


def batch(run, book: Path, payload: dict) -> None:
    code, _, err = run(["record", str(book), "--batch:stdin"], json.dumps(payload))
    assert code == 0, err


def live_book(synthetic, run) -> Path:
    book = synthetic(seed=7)
    (book / "strategies" / "baseline" / "status").write_text("live\n")
    code, _, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    return book


def propose(run, book: Path, day: str, *extra: str) -> dict:
    code, receipt, err = run(["check", str(book), "--propose", day, *extra])
    assert code == 0, err
    return receipt


def proposal(book: Path, stem: str) -> dict:
    return json.loads((book / "proposals" / f"{stem}.json").read_text())


def fills(book: Path) -> list[dict]:
    path = book / "ledger" / "fills.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


SEND_DAY = [FIRST]  # the UTC day `record` reads fills on


@pytest.fixture(autouse=True)
def on_send_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "utc_today", lambda: date.fromisoformat(SEND_DAY[0]))


def approve(book: Path, day: str) -> None:
    """The operator's reply on `day`, an approve decision dated that day: a
    planted line, since `record` stamps today."""
    decision = {
        "id": f"approve-{day}",
        "ts": f"{day}T18:00:00Z",
        "kw": ["approve", "rebalance"],
        "subject": day,
        "action": "approve",
        "reason": "approve",
    }
    append_ledger(open_book(str(book)).path_of(Kind.DECISION), [decision])


def approve_and_fill(run, book: Path, day: str) -> tuple[int, str]:
    """The operator's reply on `day` as an approve decision; then every
    order filled at its price, pasted as a table."""
    code, _, err = run(["check", str(book), day])
    assert code == 0, err
    approve(book, day)
    SEND_DAY[0] = day
    table = [
        {key: order[key] for key in ("symbol", "side", "quantity", "price")}
        | {"date": day}
        for order in proposal(book, day)["orders"]
    ]
    code, _, err = run(
        ["record", str(book), "--fills:stdin", "--proposal", day], json.dumps(table)
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


def test_two_rebalances_advise_approve_and_fill(synthetic, run):
    book = live_book(synthetic, run)
    propose(run, book, FIRST)
    first = proposal(book, FIRST)
    assert first["orders"], "the baseline sleeve proposes trades"
    view = run(["check", str(book), FIRST])[1]
    assert list(view)[:4] == ["book", "proposal", "blockers", "baseline"]
    assert view["baseline"][0]["strategy"] == "baseline"
    assert view["blockers"]["baseline"]  # no critique yet: shown, not hidden
    assert first["sleeves"]["baseline"]["weight"] == pytest.approx(0.02)

    code, err = approve_and_fill(run, book, FIRST)
    assert code == 0, err
    landed = fills(book)
    assert len(landed) == len(first["orders"])
    assert {(f["proposal"], f["strategy"], f["date"]) for f in landed} == {
        (FIRST, "baseline", FIRST)
    }
    assert positions(landed) == targets(first)

    propose(run, book, SECOND)
    second = proposal(book, SECOND)
    held = positions(landed)
    kept = set(held) & set(targets(second))
    assert kept, "some name stays in the sleeve across the two rebalances"
    for order in second["orders"]:
        assert order["held"] == held.get(order["symbol"], 0.0)
        sign = 1 if order["side"] == "buy" else -1
        assert order["held"] + sign * order["quantity"] == order["target"]
    assert not second["carried"]  # every first order filled

    code, err = approve_and_fill(run, book, SECOND)
    assert code == 0, err
    assert positions(fills(book)) == targets(second)


def test_a_fill_without_an_approval_on_or_before_it_is_refused(synthetic, run):
    book = live_book(synthetic, run)
    propose(run, book, FIRST)
    order = proposal(book, FIRST)["orders"][0]
    fill = {key: order[key] for key in ("symbol", "side", "quantity", "price")}
    fill |= {"date": FIRST, "strategy": "baseline", "proposal": FIRST}
    code, verdict, _ = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"fills": [fill]})
    )
    assert code == 1
    assert verdict["rejected"][0]["where"] == "fills[0].proposal"
    bare = fill | {"proposal": None}
    code, verdict, _ = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"fills": [bare]})
    )
    assert (code, verdict["rejected"][0]["where"]) == (1, "fills[0].proposal")
    later = {
        "kw": ["approve", "late"],
        "subject": FIRST,
        "action": "approve",
        "reason": "approve",
    }
    batch(run, book, {"decisions": [later]})  # dated today, after the fill
    code, verdict, _ = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"fills": [fill]})
    )
    assert code == 1
    assert "on or before" in verdict["rejected"][0]["fix"]
    assert fills(book) == []
    approve(book, FIRST)
    batch(run, book, {"fills": [fill]})
    assert len(fills(book)) == 1


def test_no_sleeve_exits_1_naming_the_reason(synthetic, run):
    book = synthetic(seed=7)
    code, _, err = run(["check", str(book), "--propose", FIRST])
    assert code == 1
    assert "no sleeve" in err
    (book / "strategies" / "baseline" / "status").write_text("live\n")
    code, _, err = run(["check", str(book), "--propose", FIRST])
    assert code == 1
    assert "skipped baseline" in err
    assert not (book / "proposals" / f"{FIRST}.json").exists()


def test_a_proposal_is_written_once_and_check_needs_one(synthetic, run):
    book = live_book(synthetic, run)
    code, _, err = run(["check", str(book), FIRST])
    assert code == 1
    assert "no proposal" in err
    propose(run, book, FIRST)
    code, _, err = run(["check", str(book), "--propose", FIRST])
    assert code == 1
    assert "--force" in err
    assert (
        propose(run, book, FIRST, "--force")["proposal"] == f"proposals/{FIRST}.2.json"
    )
    assert run(["check", str(book), FIRST])[1]["proposal"].endswith(".2.json")


def test_an_older_dry_run_fill_never_lands_in_a_position(synthetic, run):
    book = live_book(synthetic, run)
    propose(run, book, FIRST)
    symbol = proposal(book, FIRST)["orders"][0]["symbol"]
    dry = {
        "symbol": symbol,
        "side": "buy",
        "quantity": 100,
        "price": 10.0,
        "date": FIRST,
        "strategy": "baseline",
        "dry_run": True,
    }
    opening = dry | {"symbol": "ZZZ", "quantity": 5, "strategy": "opening"}
    del opening["dry_run"]
    batch(run, book, {"fills": [opening]})
    planted = {"id": "dry-fill", "ts": f"{FIRST}T00:00:00Z"} | dry
    append_ledger(open_book(str(book)).path_of(Kind.FILL), [planted])
    propose(run, book, FIRST, "--force")
    again = proposal(book, f"{FIRST}.2")
    order = next(o for o in again["orders"] if o["symbol"] == symbol)
    assert order["held"] == 0.0
    assert [(h["symbol"], h["strategy"]) for h in again["unmanaged"]] == [
        ("ZZZ", "baseline")
    ]


def test_an_order_over_the_adv_bound_is_cut_and_reported(synthetic, run):
    """Targets already sit inside the ADV bound; a sale of shares held from
    a looser bound is what passes it."""
    book = live_book(synthetic, run)
    propose(run, book, FIRST)
    assert approve_and_fill(run, book, FIRST)[0] == 0
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["max_adv_participation"] = BOUND  # the operator's word, applied
    path.write_text(json.dumps(limits))
    propose(run, book, SECOND)
    document = proposal(book, SECOND)
    assert document["cuts"]
    for cut in document["cuts"]:
        assert cut["kept"] < cut["wanted"]
        assert cut["adv_participation"] > cut["bound"] == BOUND
    assert all(o["adv_participation"] <= BOUND for o in document["orders"])
    view = run(["check", str(book), SECOND])[1]
    assert view["cuts"] == document["cuts"]


@pytest.mark.parametrize("rejected", [False, True])
def test_an_unfilled_order_carries_once(synthetic, run, rejected):
    book = live_book(synthetic, run)
    propose(run, book, FIRST)
    if rejected:
        reject = {
            "kw": ["skip", "first"],
            "subject": FIRST,
            "action": "reject",
            "reason": "operator skipped the day",
        }
        batch(run, book, {"decisions": [reject]})
    propose(run, book, SECOND)
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
