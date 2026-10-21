"""The operator surface: the daily loop runs with no operator input and ends
in a brief whose last line is one plain reply; a chat approval is a file
quoting the reply plus an `approve` decision hashing it; a governed file
changed without a decision warns; `README.md` names no command."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from btm_finance import onboarding
from btm_finance.brief import Owed, Reply, reply
from btm_finance.models import Answers
from btm_finance.scaffold import template

FIRST = "2016-12-30"  # the synthetic baseline's first annual rebalance
TODAY = datetime.now(UTC).date().isoformat()
VERBS = ("start", "load", "record", "measure", "check", "recommend")
UNWITNESSED = "changed without a decision hashing it"


def record(run, book: Path, payload: dict) -> dict:
    code, receipt, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps(payload)
    )
    assert code == 0, err
    return receipt


def decision(subject: str, action: str, reason: str, *applied: str) -> dict:
    return {
        "kw": [action, "chat"],
        "subject": subject,
        "action": action,
        "reason": reason,
        "applied": list(applied),
    }


def unwitnessed(run, book: Path) -> list[str]:
    view = run(["check", str(book)])[1]
    return [w["file"] for w in view["warnings"] if w.get("problem") == UNWITNESSED]


def promote(run, book: Path, word: str) -> None:
    """The operator's word in chat, applied: status written, decision hashing it."""
    (book / "strategies" / "baseline" / "status").write_text(f"{word}\n")
    reason = f"operator: move baseline to {word}"
    applied = "strategies/baseline/status"
    record(run, book, {"decisions": [decision("baseline", "promote", reason, applied)]})


def test_the_loop_runs_unattended_and_the_proposal_waits(synthetic, run):
    book = synthetic(seed=7)
    promote(run, book, "paper")
    code, view, err = run(["check", str(book)])  # loop step 2
    assert code == 0, err
    assert [w for w in view["warnings"] if w.get("problem") == UNWITNESSED] == []
    code, _, err = run(["measure", str(book), "baseline"])  # step 3
    assert code == 0, err
    code, _, err = run(["recommend", str(book), FIRST])  # step 4
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
        [line] = [line for line in lines if line.startswith(f"proposal {FIRST}")]
        ages.append(int(re.search(r"\((\d+)d old\)", line).group(1)))
        assert "baseline backtest w " in line
        assert lines[-1] == f"Reply approve, reject, or override {FIRST} with a reason."
        assert "--" not in lines[-1] and "`" not in lines[-1]
    assert ages[1] == ages[0] + 1
    assert not (book / "ledger" / "fills.jsonl").exists()
    assert list((book / "approvals").iterdir()) == []


def chat_book(run, book: Path) -> Path:
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
    file = book / "approvals" / f"{TODAY}.json"
    document = {"date": TODAY, "proposal": TODAY, "orders": [order]}
    file.write_text(json.dumps(document | {"reply": "approve, go ahead"}))
    return file


def test_a_chat_approval_passes_only_once_a_decision_hashes_it(book, run):
    file = chat_book(run, book)
    target = f"approvals/{file.name}"
    code, view, _ = run(["check", str(book), target])
    assert code == 1
    assert any("no approve decision hashes" in p for p in view["problems"])
    assert unwitnessed(run, book) == [target]
    reply_text = "approve, go ahead"
    record(run, book, {"decisions": [decision(TODAY, "approve", reply_text, target)]})
    code, view, err = run(["check", str(book), target])
    assert (code, view["problems"]) == (0, []), err
    assert unwitnessed(run, book) == []
    line = json.loads(
        (book / "ledger" / "decisions.jsonl").read_text().splitlines()[-1]
    )
    assert line["reason"] == json.loads(file.read_text())["reply"]
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == f"Paste your fills for {TODAY}."
    edited = json.loads(file.read_text())
    edited["orders"][0]["quantity"] = 20  # changed after the yes
    file.write_text(json.dumps(edited))
    code, view, _ = run(["check", str(book), target])
    assert code == 1
    assert any("no approve decision hashes" in p for p in view["problems"])


def test_an_approval_without_the_reply_fails(book, run):
    file = chat_book(run, book)
    document = json.loads(file.read_text())
    del document["reply"]
    file.write_text(json.dumps(document))
    target = f"approvals/{file.name}"
    record(run, book, {"decisions": [decision(TODAY, "approve", "yes", target)]})
    code, view, _ = run(["check", str(book), target])
    assert code == 1
    assert view["problems"] == [
        'approval needs "reply": the operator\'s words verbatim'
    ]


def test_a_hand_edit_of_limits_warns_until_a_decision_hashes_it(book, run):
    assert unwitnessed(run, book) == []
    [onboarded] = [
        json.loads(line)
        for line in (book / "ledger" / "decisions.jsonl").read_text().splitlines()
    ]
    assert (onboarded["action"], onboarded["reason"]) == ("onboard", "start")
    assert {a["path"] for a in onboarded["applied"]} == {
        "limits.json",
        "strategies/baseline/status",
    }
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["sizing"]["ruin_bound"] = 0.2
    path.write_text(json.dumps(limits))
    assert unwitnessed(run, book) == ["limits.json"]
    book_id = json.loads((book / "book.json").read_text())["id"]
    said = "operator: lower the ruin bound to 0.2"
    record(
        run, book, {"decisions": [decision(book_id, "override", said, "limits.json")]}
    )
    assert unwitnessed(run, book) == []


@pytest.mark.parametrize(
    ("path", "fix"),
    [
        ("preferences.json", "are governed"),
        ("approvals/../limits.json", "are governed"),
        ("strategies/ghost/status", "no such file"),
    ],
)
def test_applied_names_only_a_governed_file_that_exists(book, run, path, fix):
    book_id = json.loads((book / "book.json").read_text())["id"]
    entry = decision(book_id, "override", "operator said so", path)
    code, verdict, _ = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"decisions": [entry]})
    )
    assert code == 1
    assert verdict["rejected"][0]["where"] == "decisions[0].applied[0]"
    assert fix in verdict["rejected"][0]["fix"]


def test_onboard_names_the_book(book, run):
    entry = decision("baseline", "onboard", "start")
    code, verdict, _ = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"decisions": [entry]})
    )
    assert code == 1
    assert "onboard names the book" in verdict["rejected"][0]["fix"]


def test_the_last_line_follows_the_reply_order():
    late = ("drift", "2026-01-31")
    owed = Owed(unfilled="2026-10-20", unanswered="2026-10-01", pending=True, late=late)
    assert reply(owed) == "Paste your fills for 2026-10-20."
    owed = Owed(unanswered="2026-10-01", pending=True, late=late)
    assert reply(owed) == "Reply approve, reject, or override 2026-10-01 with a reason."
    assert reply(Owed(pending=True, late=late)) == Reply.CONFIRM.value
    assert reply(Owed(late=late)) == "Say what happened to drift by 2026-01-31."
    assert reply(Owed()) == Reply.NOTHING.value


def test_a_question_asked_today_asks_for_a_yes(book, run):
    pad = book / "ledger" / "pad" / "scratch.jsonl"
    entry = {"ts": f"{TODAY}T08:00:00Z", "type": "question", "body": "lower cap?"}
    pad.write_text(json.dumps(entry) + "\n")
    lines = run(["check", str(book), "--brief"])[1]["lines"]
    assert lines[-1] == "Reply yes to apply, or say what to change."
    tomorrow = (date.fromisoformat(TODAY) + timedelta(days=1)).isoformat()
    lines = run(["check", str(book), "--brief", "--today", tomorrow])[1]["lines"]
    assert lines[-1] == "Nothing to decide today; ask anything."


def test_answers_set_the_schedule_in_preferences(tmp_path, run):
    root = tmp_path / "book"
    answers = {"horizon": {"brief_hour": 6, "schedule": "daily"}}
    code, _, err = run(["start", str(root), "--answers:stdin"], json.dumps(answers))
    assert code == 0, err
    preferences = json.loads((root / "preferences.json").read_text())
    assert preferences["schedule"] == {"hour": 6, "days": "daily"}
    bad = preferences | {"schedule": {"hour": 24, "days": "daily"}}
    code, verdict, _ = run(
        ["record", str(root), "--batch:stdin"], json.dumps({"preferences": [bad]})
    )
    assert code == 1
    assert verdict["rejected"][0]["where"].startswith("preferences[0]")


@pytest.mark.parametrize("given", [{}, {"broker": {"name": "Northbank", "api": True}}])
def test_the_readme_names_no_command(given):
    setting = onboarding.Setting(
        title="b",
        dated="2026-01-02",
        cap=1000,
        held_out="/x/held.json",
        universe=True,
        binding="env uv run btm-finance",
    )
    readme = onboarding.readme(
        template("README.tmpl"), Answers.model_validate(given), setting
    )
    assert "--" not in readme and "$" not in readme and "btm-finance" not in readme
    for verb in VERBS:
        assert re.search(rf"\b{verb}\b", readme, re.IGNORECASE) is None, verb
    assert re.findall(r"`([^`]*)`", readme) == ["ledger/"]
    assert "/x/held.json" not in readme
