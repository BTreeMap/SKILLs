"""Invariant 4: `bin/send` reads only a same-day file under `approvals/`
naming an existing proposal; anything else is refused with a named reason
before any fill."""

from __future__ import annotations

import json


def test_an_approval_dated_yesterday_is_refused(book, approve, send):
    file = approve(book / "approvals" / "2026-01-01.json", "2026-01-01")
    done = send(str(file), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "approval dated '2026-01-01', today is 2026-01-02" in done.stderr
    assert not (book / "ledger" / "fills.jsonl").exists()


def test_a_same_day_approval_outside_approvals_is_refused(book, approve, send):
    file = approve(book / "approvals" / "2026-01-02.json", "2026-01-02")
    moved = book / "rejected" / file.name
    file.rename(moved)
    done = send(str(moved), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "is not a file under" in done.stderr
    assert "only approvals/ sends" in done.stderr
    assert not (book / "ledger" / "fills.jsonl").exists()


def test_a_link_inside_approvals_resolving_outside_is_refused(book, approve, send):
    file = approve(book / "approvals" / "2026-01-02.json", "2026-01-02")
    target = book / "rejected" / file.name
    file.rename(target)
    file.symlink_to(target)
    done = send(str(file), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "only approvals/ sends" in done.stderr


def test_an_approval_without_orders_is_refused(book, send):
    file = book / "approvals" / "2026-01-02.json"
    file.write_text(json.dumps({"date": "2026-01-02", "orders": []}))
    done = send(str(file), "--dry-run", "--today", "2026-01-02")
    assert done.returncode == 1
    assert "non-empty" in done.stderr


def test_an_approval_naming_no_proposal_is_refused(book, approve, send):
    file = approve(book / "approvals" / "2026-01-02.json", "2026-01-02")
    for name in ("ghost", "../limits"):
        document = json.loads(file.read_text()) | {"proposal": name}
        file.write_text(json.dumps(document))
        done = send(str(file), "--dry-run", "--today", "2026-01-02")
        assert done.returncode == 1
        assert f"proposal {name!r} names no file under" in done.stderr
