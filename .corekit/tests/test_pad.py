"""The pad: verbatim round-trips, new ids, and filtered reads."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, compile_match, pad_entries, pad_ids
from btm_corekit.store.pad import MATCH_MAX, pad_read, pad_write


class TestWrite:
    def test_mints_sequential_ids_and_round_trips_the_body(self, tmp_path):
        assert pad_write(tmp_path, {"type": "open", "q": "why?"})["written"] == "j1"
        assert (
            pad_write(tmp_path, {"free": ["any", {"shape": True}]})["written"] == "j2"
        )
        entries = pad_entries(tmp_path)
        assert entries[0]["body"] == {"type": "open", "q": "why?"}
        assert entries[1]["body"] == {"free": ["any", {"shape": True}]}
        assert pad_ids(tmp_path) == {"j1", "j2"}

    def test_body_keys_never_collide_with_the_envelope(self, tmp_path):
        pad_write(tmp_path, {"j": "fake", "t": "fake", "body": "fake"})
        entry = pad_entries(tmp_path)[0]
        assert entry["j"] == "j1"
        assert entry["body"] == {"j": "fake", "t": "fake", "body": "fake"}


class TestRead:
    def seed(self, tmp_path):
        pad_write(tmp_path, {"type": "open", "q": "cost model?"})
        pad_write(tmp_path, {"type": "extraction", "key": "doi:10.1/x"})
        pad_write(tmp_path, {"text": "arXiv wants field syntax"})

    def test_kind_and_match_and_since_filter(self, tmp_path):
        self.seed(tmp_path)
        assert pad_read(tmp_path, type_="open")["shown"] == 1
        assert pad_read(tmp_path, match="FIELD syntax")["shown"] == 1
        late = pad_read(tmp_path, since="j1")
        assert [e["j"] for e in late["entries"]] == ["j2", "j3"]
        assert late["total"] == 3

    def test_limit_keeps_the_newest(self, tmp_path):
        self.seed(tmp_path)
        assert [e["j"] for e in pad_read(tmp_path, limit=1)["entries"]] == ["j3"]

    def test_empty_pad_reads_empty(self, tmp_path):
        assert pad_read(tmp_path) == {"total": 0, "shown": 0, "entries": []}

    def test_bad_filters_are_the_only_rejections(self, tmp_path):
        self.seed(tmp_path)
        with pytest.raises(CommandError, match="j12"):
            pad_read(tmp_path, since="round-1")
        with pytest.raises(CommandError, match="--match"):
            pad_read(tmp_path, match="[")


class TestRedirectAppends:
    def test_a_bare_row_appended_by_hand_reads_as_a_body(self, tmp_path):
        pad_write(tmp_path, {"type": "open", "q": "first"})
        with (tmp_path / "scratch.jsonl").open("a") as handle:
            handle.write('{"type": "open", "q": "by redirect"}\n')
        entries = pad_entries(tmp_path)
        assert entries[1] == {
            "j": "j2",
            "t": "",
            "body": {"type": "open", "q": "by redirect"},
        }
        assert pad_write(tmp_path, {"type": "open"})["written"] == "j3"

    def test_a_mangled_line_fails_cleanly(self, tmp_path):
        (tmp_path / "scratch.jsonl").write_text("{broken\n")
        with pytest.raises(CommandError, match="not JSON"):
            pad_entries(tmp_path)


def test_compile_match_caps_length_and_reports_bad_patterns():
    assert compile_match("Ab").search("cab")
    with pytest.raises(CommandError, match="at most"):
        compile_match("a" * (MATCH_MAX + 1))
    with pytest.raises(CommandError, match="unreadable"):
        compile_match("[")
