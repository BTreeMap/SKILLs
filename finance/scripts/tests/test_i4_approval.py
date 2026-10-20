"""Invariant 4: the sender takes only a same-day file under `approvals/`;
anything else is refused with a named reason before any guard after it."""

from __future__ import annotations

import json


def test_an_approval_dated_yesterday_is_refused(book, approve, send):
    file = approve(book / "approvals" / "2026-01-01.json", "2026-01-01")
    done = send(str(file), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "approval dated '2026-01-01', today is 2026-01-02" in done.stderr
    assert not (book / "ledger" / "fills.jsonl").exists()


def test_a_same_day_approval_outside_approvals_is_refused(book, approve, send):
    file = approve(book / "proposals" / "2026-01-02.json", "2026-01-02")
    done = send(str(file), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "is not a file under" in done.stderr
    assert "only approvals/ sends" in done.stderr
    assert not (book / "ledger" / "fills.jsonl").exists()


def test_a_link_inside_approvals_resolving_outside_is_refused(book, approve, send):
    target = approve(book / "proposals" / "2026-01-02.json", "2026-01-02")
    link = book / "approvals" / "2026-01-02.json"
    link.symlink_to(target)
    done = send(str(link), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "only approvals/ sends" in done.stderr


def test_an_approval_without_orders_is_refused(book, send):
    file = book / "approvals" / "2026-01-02.json"
    file.write_text(json.dumps({"date": "2026-01-02", "orders": []}))
    done = send(str(file), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "non-empty" in done.stderr
