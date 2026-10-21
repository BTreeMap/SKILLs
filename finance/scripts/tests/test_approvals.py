"""Invariant 4: an approval passes `check` only dated today (UTC), naming an
existing proposal, every order one of it within the ADV bound on a sleeve.
`record --fills:file` and `record --dry-run` turn an approval into a `fills`
batch through the same gate, whole or not at all."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

TODAY = datetime.now(UTC).date().isoformat()
TOMORROW = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()


def set_status(book: Path, word: str, strategy: str = "baseline") -> None:
    folder = book / "strategies" / strategy
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "status").write_text(word + "\n")


def fill_lines(book: Path) -> list[dict]:
    path = book / "ledger" / "fills.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def check(run, book: Path, target: str) -> tuple[int, dict, str]:
    return run(["check", str(book), target])


def record_fills(run, book: Path, approval: str, table: Path):
    return run(
        ["record", str(book), "--fills:file", str(table), "--approval", approval]
    )


def test_a_valid_approval_passes_with_its_order_table(book, approve, run):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    code, view, err = check(run, book, f"approvals/{TODAY}.json")
    assert code == 0, err
    assert view["problems"] == []
    (order,) = view["orders"]
    assert (order["symbol"], order["strategy"], order["account"]) == (
        "ABC",
        "baseline",
        "live",
    )
    assert "record --fills:file" in view["next"]
    assert fill_lines(book) == []


def test_an_absolute_path_under_approvals_is_read(book, approve, run):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "paper")
    code, view, _ = check(run, book, str(file))
    assert (code, view["orders"][0]["account"]) == (0, "paper")


def test_an_approval_dated_another_day_fails(book, approve, run):
    approve(book / "approvals" / "2026-01-01.json", "2026-01-01")
    set_status(book, "live")
    code, view, _ = run(
        ["check", str(book), "approvals/2026-01-01.json", "--today", "2026-01-02"]
    )
    assert code == 1
    assert view["problems"] == [
        "approval dated '2026-01-01', today is 2026-01-02 (UTC): write a new "
        "approval today"
    ]


def test_an_approval_naming_no_proposal_fails(book, approve, run):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    for name in ("ghost", "../limits"):
        document = json.loads(file.read_text()) | {"proposal": name}
        file.write_text(json.dumps(document))
        code, view, _ = check(run, book, f"approvals/{TODAY}.json")
        assert code == 1
        assert f"proposal {name!r} names no file under proposals/" in view["problems"]


def test_an_order_off_the_proposal_over_adv_or_off_a_sleeve_fails(book, approve, run):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY, adv_participation=0.5)
    document = json.loads(file.read_text())
    document["orders"].append(document["orders"][0] | {"symbol": "NEW"})
    file.write_text(json.dumps(document))
    code, view, _ = check(run, book, f"approvals/{TODAY}.json")  # still research
    assert code == 1
    assert "orders[0]: adv_participation 0.5 exceeds limit 0.02" in view["problems"]
    assert (
        "orders[0]: strategy baseline is research, not paper|probe|live"
        in (view["problems"])
    )
    assert (
        "orders[1]: NEW buy baseline is no order of the proposal" in (view["problems"])
    )


def test_an_approval_without_orders_fails(book, run):
    file = book / "approvals" / f"{TODAY}.json"
    file.write_text(json.dumps({"date": TODAY, "proposal": TODAY, "orders": []}))
    code, view, _ = check(run, book, f"approvals/{TODAY}.json")
    assert code == 1
    assert any("non-empty" in problem for problem in view["problems"])


def test_a_file_outside_approvals_is_refused(book, approve, run):
    file = approve(book / "approvals" / f"{TODAY}.json", TODAY)
    moved = book / "rejected" / file.name
    file.rename(moved)
    code, _, err = check(run, book, f"rejected/{file.name}")
    assert code == 1 and "no file under the book's approvals/" in err
    file.symlink_to(moved)
    code, _, err = check(run, book, f"approvals/{file.name}")
    assert code == 1 and "no file under the book's approvals/" in err


def test_pasted_csv_fills_land_with_strategy_and_approval_stem(
    book, approve, run, tmp_path
):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    table = tmp_path / "fills.csv"
    table.write_text(f"symbol,side,quantity,price,date\nABC,buy,10,12.4,{TODAY}\n")
    code, receipt, err = record_fills(run, book, f"approvals/{TODAY}.json", table)
    assert code == 0, err
    assert receipt["accepted"] == {"fill": 1}
    (fill,) = fill_lines(book)
    assert (fill["symbol"], fill["quantity"], fill["price"]) == ("ABC", 10, 12.4)
    assert (fill["strategy"], fill["dry_run"], fill["approval"]) == (
        "baseline",
        False,
        TODAY,
    )
    view = run(["check", str(book)])[1]
    (entry,) = view["proposals"]
    assert entry["approvals"] == [{"file": f"approvals/{TODAY}.json", "filled": True}]


def test_pasted_json_fills_land(book, approve, run, tmp_path):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "probe")
    assert run(["check", str(book)])[1]["proposals"][0]["approvals"] == [
        {"file": f"approvals/{TODAY}.json", "filled": False}
    ]
    table = tmp_path / "fills.json"
    row = {"symbol": "ABC", "side": "buy", "quantity": 4, "price": 12.0}
    table.write_text(json.dumps([row | {"date": TODAY, "strategy": "baseline"}]))
    code, _, err = record_fills(run, book, f"approvals/{TODAY}.json", table)
    assert code == 0, err
    assert [f["quantity"] for f in fill_lines(book)] == [4]


def two_sleeves(book: Path) -> str:
    """One approval buying ABC in two live sleeves."""
    orders = [
        {
            "symbol": "ABC",
            "side": "buy",
            "quantity": 10,
            "price": 12.5,
            "strategy": name,
            "adv_participation": 0.001,
        }
        for name in ("baseline", "other")
    ]
    (book / "proposals" / f"{TODAY}.json").write_text(json.dumps({"orders": orders}))
    (book / "approvals" / f"{TODAY}.json").write_text(
        json.dumps({"date": TODAY, "proposal": TODAY, "orders": orders})
    )
    set_status(book, "live")
    set_status(book, "live", "other")
    return f"approvals/{TODAY}.json"


def test_a_symbol_and_side_in_two_sleeves_needs_the_strategy_column(
    book, run, tmp_path
):
    approval = two_sleeves(book)
    assert check(run, book, approval)[0] == 0
    table = tmp_path / "fills.csv"
    table.write_text(f"symbol,side,quantity,price,date\nABC,buy,10,12.4,{TODAY}\n")
    code, verdict, _ = record_fills(run, book, approval, table)
    assert code == 1
    assert verdict["rejected"] == [
        {
            "where": "fills[0]",
            "fix": "ABC buy is in baseline, other: add a strategy column",
        }
    ]
    assert fill_lines(book) == []
    table.write_text(
        f"symbol,side,quantity,price,date,strategy\nABC,buy,10,12.4,{TODAY},other\n"
    )
    code, _, err = record_fills(run, book, approval, table)
    assert code == 0, err
    assert [f["strategy"] for f in fill_lines(book)] == ["other"]


def test_any_fill_naming_no_order_refuses_the_whole_table(book, approve, run, tmp_path):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "live")
    table = tmp_path / "fills.csv"
    table.write_text(
        "symbol,side,quantity,price,date\n"
        f"ABC,buy,5,12.4,{TODAY}\nXYZ,buy,5,3.0,{TODAY}\nABC,buy,5,12.4,{TOMORROW}\n"
    )
    code, verdict, _ = record_fills(run, book, f"approvals/{TODAY}.json", table)
    assert code == 1
    assert [r["where"] for r in verdict["rejected"]] == ["fills[1]", "fills[2]"]
    assert "XYZ buy names no order of the approval" in verdict["rejected"][0]["fix"]
    assert "is after today" in verdict["rejected"][1]["fix"]
    assert fill_lines(book) == []


def test_a_real_fill_on_a_paper_sleeve_is_refused(book, approve, run, tmp_path):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "paper")
    table = tmp_path / "fills.csv"
    table.write_text(f"symbol,side,quantity,price,date\nABC,buy,10,12.4,{TODAY}\n")
    code, verdict, _ = record_fills(run, book, f"approvals/{TODAY}.json", table)
    assert code == 1
    assert "--dry-run" in verdict["rejected"][0]["fix"]


def test_a_header_missing_a_fill_key_is_refused(book, approve, run, tmp_path):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    table = tmp_path / "fills.csv"
    table.write_text("symbol,side,quantity\nABC,buy,10\n")
    code, _, err = record_fills(run, book, f"approvals/{TODAY}.json", table)
    assert code == 1 and "header lacks price, date" in err


def test_dry_run_records_paper_orders_at_price(book, approve, run):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    set_status(book, "paper")
    code, _, err = run(
        ["record", str(book), "--approval", f"approvals/{TODAY}.json", "--dry-run"]
    )
    assert code == 0, err
    assert [
        (f["symbol"], f["price"], f["dry_run"], f["date"], f["approval"])
        for f in fill_lines(book)
    ] == [("ABC", 12.5, True, TODAY, TODAY)]


def test_dry_run_refuses_a_file_holding_a_live_or_probe_order(book, approve, run):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    for word in ("live", "probe"):
        set_status(book, word)
        code, verdict, _ = run(
            ["record", str(book), "--approval", f"approvals/{TODAY}.json", "--dry-run"]
        )
        assert code == 1
        assert "trades the real account" in verdict["rejected"][0]["fix"]
    assert fill_lines(book) == []


def test_dry_run_refuses_an_approval_check_fails(book, approve, run):
    approve(book / "approvals" / "2026-01-01.json", "2026-01-01")
    set_status(book, "paper")
    code, verdict, _ = run(
        ["record", str(book), "--approval", "approvals/2026-01-01.json", "--dry-run"]
    )
    assert code == 1
    assert "approval dated '2026-01-01'" in verdict["rejected"][0]["fix"]
    assert fill_lines(book) == []


def test_the_sugar_flags_need_each_other(book, approve, run, tmp_path):
    approve(book / "approvals" / f"{TODAY}.json", TODAY)
    approval = f"approvals/{TODAY}.json"
    code, _, err = run(["record", str(book), "--dry-run"])
    assert code == 1 and "need --approval" in err
    code, _, err = run(["record", str(book), "--approval", approval])
    assert code == 1 and "one of --fills:file or --dry-run" in err
    batch = tmp_path / "batch.json"
    batch.write_text("{}")
    code, _, err = run(
        ["record", str(book), "--approval", approval, "--batch:file", str(batch)]
    )
    assert code == 1 and "drop --batch" in err
