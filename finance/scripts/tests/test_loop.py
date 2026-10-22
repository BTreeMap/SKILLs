"""The operator surface: the daily loop runs with no operator input and ends
in a brief whose last line is one plain reply; a chat approval is an
`approve` decision quoting the reply, after which the brief asks for fills
until a fill names the proposal."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from btm_finance.brief import Owed, Reply, reply

FIRST = "2016-12-30"  # the synthetic baseline's first annual rebalance
TODAY = datetime.now(UTC).date().isoformat()


def record(run, book: Path, payload: dict) -> dict:
    code, receipt, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps(payload)
    )
    assert code == 0, err
    return receipt


def decision(subject: str, action: str, reason: str) -> dict:
    return {
        "kw": [action, "chat"],
        "subject": subject,
        "action": action,
        "reason": reason,
    }


def promote(run, book: Path, word: str) -> None:
    """The operator's word in chat, applied: status written, decision
    recorded."""
    (book / "strategies" / "baseline" / "status").write_text(f"{word}\n")
    reason = f"operator: move baseline to {word}"
    record(run, book, {"decisions": [decision("baseline", "promote", reason)]})


def test_the_loop_runs_unattended_and_the_proposal_waits(synthetic, run):
    book = synthetic(seed=7)
    promote(run, book, "live")
    code, view, err = run(["check", str(book)])  # loop step 2
    assert code == 0, err
    assert view["warnings"] == []
    code, _, err = run(["measure", str(book), "baseline"])  # step 3
    assert code == 0, err
    code, _, err = run(["check", str(book), "--propose", FIRST])  # step 4
    assert code == 0, err
    code, _, err = run(["check", str(book), FIRST])
    assert code == 0, err
    day = datetime.now(UTC).date()
    ages = []
    for today in (day, day + timedelta(days=1)):
        code, brief, err = run(["check", str(book), "--brief", "--today", str(today)])
        assert code == 0, err
        lines = brief["lines"]
        assert len(lines) <= 12
        assert lines[0] == "cap 10000000, book 0"
        [line] = [line for line in lines if line.startswith(f"proposal {FIRST}")]
        ages.append(int(re.search(r"\((\d+)d old\)", line).group(1)))
        assert "baseline backtest w " in line
        assert lines[-1] == f"Reply approve, reject, or override {FIRST} with a reason."
        assert "--" not in lines[-1] and "`" not in lines[-1]
    assert ages[1] == ages[0] + 1
    assert (book / "ledger" / "fills.jsonl").read_text() == ""


def chat_book(run, book: Path) -> dict:
    """An open proposal of today holding one live order."""
    order = {
        "symbol": "ABC",
        "side": "buy",
        "quantity": 10,
        "price": 12.5,
        "strategy": "baseline",
        "adv_participation": 0.001,
    }
    (book / "proposals" / f"{TODAY}.json").write_text(json.dumps({"orders": [order]}))
    promote(run, book, "live")
    return order


def test_a_chat_approval_is_a_decision_then_the_brief_asks_for_fills(book, run):
    order = chat_book(run, book)
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == f"Reply approve, reject, or override {TODAY} with a reason."
    said = "approve, go ahead"
    receipt = record(run, book, {"decisions": [decision(TODAY, "approve", said)]})
    line = json.loads(
        (book / "ledger" / "decisions.jsonl").read_text().splitlines()[-1]
    )
    assert line["id"] in receipt["new"]["decisions"].values()
    assert (line["subject"], line["reason"]) == (TODAY, said)
    assert "applied" not in line and "objects" not in line
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == f"Paste your fills for {TODAY}."
    table = [{key: order[key] for key in ("symbol", "side", "quantity", "price")}]
    code, _, err = run(
        ["record", str(book), "--fills:stdin", "--proposal", TODAY],
        json.dumps([table[0] | {"date": TODAY}]),
    )
    assert code == 0, err
    (fill,) = map(
        json.loads, (book / "ledger" / "fills.jsonl").read_text().splitlines()
    )
    assert (fill["proposal"], fill["strategy"]) == (TODAY, "baseline")
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == "Nothing to decide today; ask anything."


def test_fills_name_a_proposal_file(book, run):
    code, _, err = run(
        ["record", str(book), "--fills:stdin", "--proposal", "2020-01-01"], "[]"
    )
    assert code == 1
    assert "names no file under proposals/" in err
    code, _, err = run(["record", str(book), "--fills:stdin"], "[]")
    assert code == 1
    assert "--fills:file needs --proposal" in err


def test_the_last_line_follows_the_reply_order():
    owed = Owed(unfilled="2026-10-20", unanswered="2026-10-01", pending=True)
    assert reply(owed) == "Paste your fills for 2026-10-20."
    owed = Owed(unanswered="2026-10-01", pending=True)
    assert reply(owed) == "Reply approve, reject, or override 2026-10-01 with a reason."
    assert reply(Owed(pending=True)) == Reply.CONFIRM.value
    assert reply(Owed()) == Reply.NOTHING.value
    assert len(Reply) == 4


def test_a_question_asked_today_asks_for_a_yes(book, run):
    pad = book / "ledger" / "pad" / "scratch.jsonl"
    entry = {"ts": f"{TODAY}T08:00:00Z", "type": "question", "body": "lower cap?"}
    pad.write_text(json.dumps(entry) + "\n")
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == "Reply yes to apply, or say what to change."
    tomorrow = (date.fromisoformat(TODAY) + timedelta(days=1)).isoformat()
    lines = run(["check", str(book), "--brief", "--today", tomorrow])[1]["lines"]
    assert lines[-1] == "Nothing to decide today; ask anything."


def test_an_answer_naming_the_question_closes_the_yes_line(book, run):
    pad = book / "ledger" / "pad" / "scratch.jsonl"
    asked = {"ts": f"{TODAY}T08:00:00Z", "type": "question", "body": "lower cap?"}
    stray = {"ts": f"{TODAY}T09:00:00Z", "type": "answer", "question": "other"}
    pad.write_text(json.dumps(asked) + "\n" + json.dumps(stray) + "\n")
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == "Reply yes to apply, or say what to change."
    answer = {
        "ts": f"{TODAY}T09:30:00Z",
        "type": "answer",
        "question": asked["ts"],
        "text": "yes, lower it",
    }
    with pad.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(answer) + "\n")
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == "Nothing to decide today; ask anything."
    code, schema, _ = run(["check", "--schema", "pad"])
    assert code == 0 and "answer" in json.dumps(schema)
