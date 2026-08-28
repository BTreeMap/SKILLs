"""The shapes hoisted out of the members: channels, files, identity, store."""

from __future__ import annotations

import argparse
import json

import pytest

from btm_corekit import (
    CommandError,
    SessionStore,
    append_jsonl,
    emit,
    read_jsonl,
    request_identity,
    run_cli,
    signal,
    user_agent,
    write_atomic,
)


class TestChannels:
    def test_emit_prints_one_json_document_to_stdout(self, capsys):
        emit({"a": 1})
        out, err = capsys.readouterr()
        assert json.loads(out) == {"a": 1}
        assert err == ""

    def test_signal_prints_a_prefixed_line_to_stderr(self, capsys):
        signal("watch this")
        out, err = capsys.readouterr()
        assert out == ""
        assert err == "signal: watch this\n"


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


class TestRequestIdentity:
    def test_a_verbatim_override_wins(self, monkeypatch):
        monkeypatch.setenv("BTM_USER_AGENT", "my-agent/2")
        monkeypatch.setenv("BTM_CONTACT", "me@example.org")
        assert user_agent("alpha") == "my-agent/2"

    def test_a_contact_derives_the_header(self, monkeypatch):
        monkeypatch.delenv("BTM_USER_AGENT", raising=False)
        monkeypatch.setenv("BTM_CONTACT", "me@example.org")
        assert user_agent("alpha") == "btm-skills/1.0 (alpha; mailto:me@example.org)"

    def test_the_project_contact_is_the_floor(self, monkeypatch):
        monkeypatch.delenv("BTM_USER_AGENT", raising=False)
        monkeypatch.delenv("BTM_CONTACT", raising=False)
        assert "skills@oss.joefang.org" in request_identity().address


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    return SessionStore("alpha", marker="meta.json", hint="run init first")


def make_session(store: SessionStore, name: str) -> None:
    directory = store.root() / name
    directory.mkdir(parents=True)
    (directory / "meta.json").write_text("{}", encoding="utf-8")


class TestSessionStore:
    def test_a_full_identifier_resolves_exactly(self, store):
        make_session(store, "deep-sea-abc123")
        assert store.dir_of("deep-sea-abc123") == store.root() / "deep-sea-abc123"

    def test_a_keyword_subset_recovers_with_a_signal(self, store, capsys):
        make_session(store, "deep-sea-abc123")
        assert store.dir_of("sea") == store.root() / "deep-sea-abc123"
        assert "recovered" in capsys.readouterr().err

    def test_a_path_argument_stands_as_given(self, store, tmp_path):
        assert store.dir_of(str(tmp_path / "x")) == tmp_path / "x"

    def test_clean_lists_sessions_with_sizes(self, store):
        make_session(store, "deep-sea-abc123")
        listing = store.clean(None, remove_all=False)
        assert [row["session"] for row in listing["sessions"]] == ["deep-sea-abc123"]

    def test_clean_refuses_a_directory_without_the_marker(self, store):
        (store.root() / "stray").mkdir(parents=True)
        with pytest.raises(CommandError, match="refusing"):
            store.clean("stray", remove_all=False)

    def test_clean_removes_one_session_and_reports_bytes(self, store):
        make_session(store, "deep-sea-abc123")
        report = store.clean("deep-sea-abc123", remove_all=False)
        assert report["bytes_freed"] > 0
        assert store.ids() == []

    def test_clean_all_with_a_session_is_refused(self, store):
        with pytest.raises(CommandError, match="one of the two"):
            store.clean("deep-sea-abc123", remove_all=True)


class TestRunCli:
    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(required=True)
        boom = sub.add_parser("boom")
        boom.set_defaults(func=self.boom)
        return parser

    @staticmethod
    def boom(args: argparse.Namespace) -> int:
        raise CommandError("told you")

    def test_command_error_becomes_exit_1_on_stderr(self, capsys):
        assert run_cli(self.parser(), ["boom"]) == 1
        assert "error: told you" in capsys.readouterr().err
