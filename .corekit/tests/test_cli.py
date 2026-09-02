"""The process boundary: CommandError exits 1, UpstreamError 2, on stderr."""

from __future__ import annotations

import argparse
import json

import pytest

from btm_corekit import (
    CommandError,
    Diagnostic,
    SessionStore,
    UpstreamError,
    read_batch,
    rejection,
    run_cli,
    wire_clean,
    wire_pad,
)


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser()
    sub = built.add_subparsers(required=True)
    boom = sub.add_parser("boom")
    boom.set_defaults(func=explode)
    down = sub.add_parser("down")
    down.set_defaults(func=unreachable)
    return built


def explode(args: argparse.Namespace) -> int:
    raise CommandError("told you")


def unreachable(args: argparse.Namespace) -> int:
    raise UpstreamError("api is down")


class TestRunCli:
    def test_command_error_becomes_exit_1_on_stderr(self, capsys):
        assert run_cli(parser(), ["boom"]) == 1
        assert "error: told you" in capsys.readouterr().err

    def test_upstream_error_becomes_exit_2_on_stderr(self, capsys):
        assert run_cli(parser(), ["down"]) == 2
        assert "error: api is down" in capsys.readouterr().err


class TestBatchAndWiring:
    def test_read_batch_reads_a_file_and_locates_bad_json(self, tmp_path):
        good = tmp_path / "b.json"
        good.write_text('{"a": 1}')
        assert read_batch(str(good)) == {"a": 1}
        bad = tmp_path / "bad.json"
        bad.write_text("{")
        verdict = read_batch(str(bad))
        assert isinstance(verdict, Diagnostic) and verdict.where == "$"
        empty = tmp_path / "e.json"
        empty.write_text(" ")
        with pytest.raises(CommandError):
            read_batch(str(empty))

    def test_rejection_envelope_names_what_stayed_put(self):
        view = rejection([Diagnostic("w", "f")], "ledger")
        assert view["unchanged"] == "ledger"
        assert view["rejected"] == [{"where": "w", "fix": "f"}]

    def test_wire_pad_and_clean_round_trip(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
        store = SessionStore("beta", marker="meta.json", hint="run init first")
        made = store.create("one two")
        store.write_meta(made.directory, {})
        parser = argparse.ArgumentParser()
        commands = parser.add_subparsers(dest="command", required=True)
        wire_pad(commands, lambda args: store.directory(args.session))
        wire_clean(commands, store)
        assert run_cli(parser, ["jot", made.name, '{"kind": "k"}']) == 0
        assert json.loads(capsys.readouterr().out)["jotted"] == "j1"
        assert run_cli(parser, ["recall", made.name, "--kind", "k"]) == 0
        assert json.loads(capsys.readouterr().out)["shown"] == 1
        assert run_cli(parser, ["clean", made.name]) == 0
        assert json.loads(capsys.readouterr().out)["bytes_freed"] > 0
