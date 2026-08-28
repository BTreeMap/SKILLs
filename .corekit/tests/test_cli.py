"""The process boundary: CommandError becomes exit 1 on stderr."""

from __future__ import annotations

import argparse

from btm_corekit import CommandError, run_cli


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser()
    sub = built.add_subparsers(required=True)
    boom = sub.add_parser("boom")
    boom.set_defaults(func=explode)
    return built


def explode(args: argparse.Namespace) -> int:
    raise CommandError("told you")


class TestRunCli:
    def test_command_error_becomes_exit_1_on_stderr(self, capsys):
        assert run_cli(parser(), ["boom"]) == 1
        assert "error: told you" in capsys.readouterr().err
