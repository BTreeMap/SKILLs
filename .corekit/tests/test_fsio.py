"""Filesystem laws: whole-file replacement and JSONL round trips."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, append_jsonl, read_jsonl, write_atomic


class TestWriteAtomic:
    def test_the_file_is_replaced_whole(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_text("before", encoding="utf-8")
        write_atomic(path, "after")
        assert path.read_text(encoding="utf-8") == "after"

    def test_no_temporary_file_survives(self, tmp_path):
        path = tmp_path / "f.json"
        write_atomic(path, "text")
        assert [p.name for p in tmp_path.iterdir()] == ["f.json"]


class TestJsonl:
    def test_records_append_in_order(self, tmp_path):
        path = tmp_path / "log.jsonl"
        path.touch()
        append_jsonl(path, [{"n": 1}])
        append_jsonl(path, [{"n": 2}, {"n": 3}])
        assert [record["n"] for record in read_jsonl(path)] == [1, 2, 3]

    def test_an_empty_file_reads_as_empty(self, tmp_path):
        path = tmp_path / "log.jsonl"
        path.touch()
        assert read_jsonl(path) == []

    @pytest.mark.parametrize(
        ("line", "fault"), [("{broken", "line 2 is not JSON"), ("[1]", "line 2 is not")]
    )
    def test_a_line_that_is_no_object_is_a_located_rejection(
        self, tmp_path, line, fault
    ):
        """Before, a mangled line escaped as a JSONDecodeError traceback from
        every log reader but the two that caught it themselves."""
        path = tmp_path / "log.jsonl"
        path.write_text('{"n": 1}\n' + line + "\n", encoding="utf-8")
        with pytest.raises(CommandError, match=fault):
            read_jsonl(path)
