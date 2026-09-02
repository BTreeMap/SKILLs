"""EventLog: stamped appends, reads, and the cap."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, EventLog


class TestEventLog:
    def test_append_stamps_and_read_returns_in_order(self, tmp_path):
        log = EventLog(tmp_path / "s" / "ledger.jsonl")
        log.touch()
        log.append([{"e": "a"}, {"e": "b"}])
        rows = log.read()
        assert [r["e"] for r in rows] == ["a", "b"]
        assert all(r["t"] for r in rows)
        assert log.count() == 2

    def test_reading_a_missing_log_names_the_hint(self, tmp_path):
        with pytest.raises(CommandError, match="run init first"):
            EventLog(tmp_path / "ledger.jsonl").read()

    def test_the_cap_counts_the_whole_log(self, tmp_path):
        log = EventLog(tmp_path / "ledger.jsonl", cap=2)
        log.touch()
        log.append([{"e": "a"}])
        with pytest.raises(CommandError, match="exceed 2"):
            log.append([{"e": "b"}, {"e": "c"}])
        assert log.count() == 1
