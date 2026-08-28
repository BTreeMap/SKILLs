"""Filesystem laws: whole-file replacement and JSONL round trips."""

from __future__ import annotations

from btm_corekit import append_jsonl, read_jsonl, write_atomic


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
