"""The process boundary: CommandError exits 1, UpstreamError 2, on stderr."""

from __future__ import annotations

import argparse
import io
import json

import pytest

from btm_corekit import (
    CommandError,
    Diagnostic,
    Model,
    NonEmpty,
    Parser,
    SessionStore,
    UpstreamError,
    content,
    read_batch,
    rejection,
    run_cli,
    wire_clean,
    wire_pad,
)
from btm_corekit.cli import (
    ARGV_MESSAGE_MAX,
    BATCH,
    ENTRY,
    FromFile,
    FromStdin,
    Inline,
    bounded,
    read_payload,
    sole_source,
)


class Marker(Model):
    k: int = 0


def parser() -> argparse.ArgumentParser:
    built = Parser()
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
        store.write_meta(made.directory, Marker())
        parser = Parser()
        commands = parser.add_subparsers(dest="command", required=True)
        wire_pad(commands, lambda args: store.directory(args.session))
        wire_clean(commands, store)
        monkeypatch.setattr("sys.stdin", io.StringIO('{"kind": "k"}'))
        assert run_cli(parser, ["jot", made.name]) == 0
        assert json.loads(capsys.readouterr().out)["jotted"] == "j1"
        assert run_cli(parser, ["recall", made.name, "--kind", "k"]) == 0
        assert json.loads(capsys.readouterr().out)["shown"] == 1
        assert run_cli(parser, ["clean", made.name]) == 0
        assert json.loads(capsys.readouterr().out)["bytes_freed"] > 0


class TestPayloadSource:
    """One decoder, three spellings, and the ambiguous case is a rejection
    rather than a silently dropped file."""

    def test_stdin_is_the_default_source(self):
        assert sole_source(None, None) == FromStdin()

    def test_a_file_argument_names_a_path(self, tmp_path):
        assert sole_source(None, str(tmp_path / "x.json")) == FromFile(
            tmp_path / "x.json"
        )

    def test_an_inline_argument_carries_its_text(self):
        assert sole_source('{"a": 1}', None) == Inline('{"a": 1}')

    def test_both_spellings_at_once_is_refused(self):
        with pytest.raises(CommandError, match="give one"):
            sole_source('{"a": 1}', "some.json")

    def test_reading_is_total_over_the_three_variants(self, tmp_path):
        path = tmp_path / "b.json"
        path.write_text('{"b": 2}')
        assert read_payload(Inline("x"), BATCH) == "x"
        assert read_payload(FromFile(path), BATCH) == '{"b": 2}'

    def test_an_empty_payload_names_only_the_offered_spellings(self):
        with pytest.raises(CommandError, match="stdin or --file"):
            read_payload(Inline("   "), BATCH)
        with pytest.raises(CommandError, match="stdin or --file"):
            read_payload(Inline("   "), ENTRY)


class TestBatchShape:
    def test_a_bare_array_is_not_a_batch(self, tmp_path):
        path = tmp_path / "b.json"
        path.write_text("[1, 2]")
        with pytest.raises(CommandError, match="one JSON object"):
            read_batch(str(path))


class TestArgvBoundary:
    """argv is untrusted input like any other: decoded, bounded, exit 1."""

    def parser(self) -> Parser:
        built = Parser(prog="t")
        commands = built.add_subparsers(dest="command", required=True)
        one = commands.add_parser("one")
        one.add_argument("--flag")
        one.set_defaults(func=lambda args: 0)
        return built

    def test_subparsers_inherit_the_decoding_parser(self):
        commands = self.parser()._subparsers
        assert commands is not None

    def test_a_malformed_argument_line_exits_one_not_two(self, capsys):
        # 2 means the upstream failed and a retry may succeed. A typo in argv
        # never succeeds on retry, so it has to land in the exit-1 column.
        assert run_cli(self.parser(), ["one", "--nope"]) == 1
        assert "error:" in capsys.readouterr().err

    def test_an_unknown_subcommand_is_a_located_rejection(self, capsys):
        assert run_cli(self.parser(), ["two"]) == 1
        assert "invalid choice" in capsys.readouterr().err

    def test_an_oversized_token_is_named_rather_than_echoed(self, capsys):
        payload = "x" * 5000
        assert run_cli(self.parser(), ["one", payload]) == 1
        err = capsys.readouterr().err
        assert len(err) < ARGV_MESSAGE_MAX * 2
        assert "belongs on stdin" in err
        assert payload not in err

    def test_a_short_message_is_passed_through_whole(self):
        assert bounded("plain") == "plain"

    def test_help_still_exits_through_argparse(self):
        with pytest.raises(SystemExit) as exit_info:
            run_cli(self.parser(), ["--help"])
        assert exit_info.value.code == 0


class TestContentChannel:
    """Free-form fields arrive as one JSON object, parsed at one boundary."""

    class Asked(Model):
        question: NonEmpty
        focus: str | None = None

    def test_stdin_json_becomes_the_parsed_record(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO('{"question": "why"}'))
        asked = content(self.Asked, None, "the framing")
        assert asked.question == "why"
        assert asked.focus is None

    def test_a_file_is_the_same_channel(self, tmp_path):
        path = tmp_path / "c.json"
        path.write_text('{"question": "why", "focus": "f"}')
        assert content(self.Asked, str(path), "the framing").focus == "f"

    def test_shell_metacharacters_survive_the_channel(self, monkeypatch):
        """The point of the channel: quotes, braces and backslashes reach the
        process unrewritten, where an argument would have been mangled."""
        hostile = 'all:"phrase" & $HOME | \\d{4} `x` (a|b)'
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"question": hostile})))
        assert content(self.Asked, None, "the framing").question == hostile

    def test_a_missing_required_field_is_located(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO('{"focus": "f"}'))
        with pytest.raises(CommandError, match="question"):
            content(self.Asked, None, "the framing")

    def test_broken_json_names_the_position(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
        with pytest.raises(CommandError, match="valid JSON"):
            content(self.Asked, None, "the framing")

    def test_a_bare_array_is_refused(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("[1, 2]"))
        with pytest.raises(CommandError, match="one JSON object"):
            content(self.Asked, None, "the framing")

    def test_empty_content_names_both_spellings(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("   "))
        with pytest.raises(CommandError, match="stdin or --file"):
            content(self.Asked, None, "the framing")
