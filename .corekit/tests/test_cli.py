"""The process boundary: content slots, and CommandError exits 1 on stderr."""

from __future__ import annotations

import argparse
import io
import json

import pytest

from btm_corekit import (
    BATCH,
    CommandError,
    Diagnostic,
    FromFile,
    FromStdin,
    Inline,
    Model,
    NonEmpty,
    Optional,
    Parser,
    Required,
    SessionStore,
    UpstreamError,
    add_slot,
    content,
    read_batch,
    read_source,
    rejection,
    run_cli,
    source_of,
    wire_clean,
    wire_pad,
)
from btm_corekit.cli import ARGV_MESSAGE_MAX, bounded

DRAFT = Required("draft", inline=False)
NOTE = Optional("note")


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


def slotted(*slots) -> Parser:
    """A parser carrying nothing but the slots under test."""
    built = Parser(prog="t")
    commands = built.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.set_defaults(func=lambda args: 0)
    for slot in slots:
        add_slot(run, slot, "shape")
    return built


def parsed(*argv: str, slots=(BATCH,)) -> argparse.Namespace:
    return slotted(*slots).parse_args(["run", *argv])


def subcommand(*slots) -> argparse.ArgumentParser:
    return slotted(*slots)._subparsers._group_actions[0].choices["run"]


def flags_of(*slots) -> set[str]:
    return {
        option
        for action in subcommand(*slots)._actions
        for option in action.option_strings
    }


class TestRunCli:
    def test_command_error_becomes_exit_1_on_stderr(self, capsys):
        assert run_cli(parser(), ["boom"]) == 1
        assert "error: told you" in capsys.readouterr().err

    def test_upstream_error_becomes_exit_2_on_stderr(self, capsys):
        assert run_cli(parser(), ["down"]) == 2
        assert "error: api is down" in capsys.readouterr().err


class TestSlotSurface:
    """One declaration generates the whole family, so no two slots drift."""

    def test_a_json_slot_offers_a_path_and_the_pipe_but_no_inline(self):
        flags = flags_of(BATCH)
        assert {"--batch:file", "--batch:stdin"} <= flags
        assert "--batch" not in flags

    def test_an_inline_slot_adds_its_own_name(self):
        assert {"--note", "--note:file", "--note:stdin"} <= flags_of(NOTE)

    def test_a_json_slot_documents_its_shape_in_the_description(self):
        assert "batch from --batch:file, --batch:stdin, the pipe: shape" in (
            subcommand(BATCH).description or ""
        )

    def test_a_second_json_slot_documents_itself_beside_the_first(self):
        described = subcommand(BATCH, Optional("aside", inline=False)).description or ""
        assert "batch from" in described and "aside from" in described

    def test_two_required_slots_are_a_declaration_defect(self):
        # Both would fall back to one stdin, and the second would read the
        # stream the first drained. A defect at wiring, not an input error.
        with pytest.raises(ValueError, match="at most one required slot"):
            slotted(BATCH, Required("other", inline=False))


class TestProvenance:
    """The truth table: one provenance per slot, stdin affine across them."""

    def test_a_path_names_a_file(self, tmp_path):
        args = parsed("--batch:file", str(tmp_path / "b.json"))
        assert source_of(BATCH, args) == FromFile(tmp_path / "b.json")

    def test_a_stdin_claim_is_the_pipe(self):
        assert source_of(BATCH, parsed("--batch:stdin")) == FromStdin()

    def test_an_inline_value_carries_its_text(self):
        assert source_of(NOTE, parsed("--note", "hi", slots=(NOTE,))) == Inline("hi")

    def test_a_required_slot_falls_back_to_the_pipe(self):
        assert source_of(BATCH, parsed()) == FromStdin()

    def test_an_optional_slot_stays_absent(self):
        assert source_of(NOTE, parsed(slots=(NOTE,))) is None

    def test_two_provenances_for_one_slot_are_refused(self, tmp_path):
        args = parsed("--note", "hi", "--note:file", str(tmp_path), slots=(NOTE,))
        with pytest.raises(CommandError, match="came from --note and --note:file"):
            source_of(NOTE, args)

    def test_a_second_stdin_claim_is_refused(self):
        with pytest.raises(CommandError, match="stdin is claimed by --batch:stdin"):
            parsed("--batch:stdin", "--note:stdin", slots=(BATCH, NOTE))

    def test_a_required_slot_says_so_when_another_slot_took_the_pipe(self):
        args = parsed("--note:stdin", slots=(BATCH, NOTE))
        with pytest.raises(CommandError, match="stdin is claimed by --note:stdin"):
            source_of(BATCH, args)


class TestNoSigils:
    """argv content is never reinterpreted, so a regex needs no escape."""

    def test_an_at_sign_starts_no_path(self):
        assert source_of(NOTE, parsed("--note", "@article", slots=(NOTE,))) == Inline(
            "@article"
        )

    def test_a_lone_dash_is_a_literal(self):
        assert source_of(NOTE, parsed("--note", "-", slots=(NOTE,))) == Inline("-")


class TestReading:
    def test_reading_is_total_over_the_three_variants(self, tmp_path, monkeypatch):
        path = tmp_path / "b.json"
        path.write_text('{"b": 2}')
        monkeypatch.setattr("sys.stdin", io.StringIO("piped"))
        assert read_source(BATCH, Inline("x")) == "x"
        assert read_source(BATCH, FromFile(path)) == '{"b": 2}'
        assert read_source(BATCH, FromStdin()) == "piped"

    def test_an_unreadable_path_is_a_rejection_not_a_traceback(self, tmp_path):
        with pytest.raises(CommandError, match="cannot read"):
            read_source(BATCH, FromFile(tmp_path / "absent"))

    def test_an_empty_source_names_every_spelling(self):
        with pytest.raises(CommandError, match="--batch:file, --batch:stdin, the pipe"):
            read_source(BATCH, Inline("   "))
        with pytest.raises(CommandError, match="--note, --note:file, --note:stdin"):
            read_source(NOTE, Inline("   "))


class TestBatchAndWiring:
    def test_read_batch_reads_a_file_and_locates_bad_json(self, tmp_path):
        good = tmp_path / "b.json"
        good.write_text('{"a": 1}')
        assert read_batch(BATCH, parsed("--batch:file", str(good))) == {"a": 1}
        bad = tmp_path / "bad.json"
        bad.write_text("{")
        verdict = read_batch(BATCH, parsed("--batch:file", str(bad)))
        assert isinstance(verdict, Diagnostic) and verdict.where == "$"

    def test_a_bare_array_is_not_a_batch(self, tmp_path):
        path = tmp_path / "b.json"
        path.write_text("[1, 2]")
        with pytest.raises(CommandError, match="one JSON object"):
            read_batch(BATCH, parsed("--batch:file", str(path)))

    def test_rejection_envelope_names_what_stayed_put_and_the_cheap_retry(self):
        view = rejection([Diagnostic("w", "f")], "ledger", BATCH)
        assert view["unchanged"] == "ledger"
        assert view["rejected"] == [{"where": "w", "fix": "f"}]
        assert "--batch:file" in view["next"]

    def test_wire_pad_and_clean_round_trip(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
        store = SessionStore("beta", marker="meta.json", hint="run init first")
        made = store.create("one two")
        store.write_meta(made.directory, Marker())
        built = Parser()
        commands = built.add_subparsers(dest="command", required=True)
        wire_pad(commands, lambda args: store.directory(args.session))
        wire_clean(commands, store)
        monkeypatch.setattr("sys.stdin", io.StringIO('{"kind": "k"}'))
        assert run_cli(built, ["jot", made.name]) == 0
        assert json.loads(capsys.readouterr().out)["jotted"] == "j1"
        assert run_cli(built, ["recall", made.name, "--kind", "k"]) == 0
        assert json.loads(capsys.readouterr().out)["shown"] == 1
        assert run_cli(built, ["clean", made.name]) == 0
        assert json.loads(capsys.readouterr().out)["bytes_freed"] > 0


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
        assert "belongs on the pipe" in err
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

    def piped(self, monkeypatch, raw: str) -> argparse.Namespace:
        monkeypatch.setattr("sys.stdin", io.StringIO(raw))
        return parsed(slots=(DRAFT,))

    def test_the_pipe_becomes_the_parsed_record(self, monkeypatch):
        asked = content(self.Asked, DRAFT, self.piped(monkeypatch, '{"question": "w"}'))
        assert asked.question == "w"
        assert asked.focus is None

    def test_a_file_is_the_same_channel(self, tmp_path):
        path = tmp_path / "c.json"
        path.write_text('{"question": "why", "focus": "f"}')
        args = parsed("--draft:file", str(path), slots=(DRAFT,))
        assert content(self.Asked, DRAFT, args).focus == "f"

    def test_shell_metacharacters_survive_the_channel(self, monkeypatch):
        """The point of the channel: quotes, braces and backslashes reach the
        process unrewritten, where an argument would have been mangled."""
        hostile = 'all:"phrase" & $HOME | \\d{4} `x` (a|b)'
        args = self.piped(monkeypatch, json.dumps({"question": hostile}))
        assert content(self.Asked, DRAFT, args).question == hostile

    def test_a_missing_required_field_is_located(self, monkeypatch):
        with pytest.raises(CommandError, match="question"):
            content(self.Asked, DRAFT, self.piped(monkeypatch, '{"focus": "f"}'))

    def test_broken_json_names_the_position(self, monkeypatch):
        with pytest.raises(CommandError, match="valid JSON"):
            content(self.Asked, DRAFT, self.piped(monkeypatch, "{not json"))

    def test_a_bare_array_is_refused(self, monkeypatch):
        with pytest.raises(CommandError, match="one JSON object"):
            content(self.Asked, DRAFT, self.piped(monkeypatch, "[1, 2]"))
