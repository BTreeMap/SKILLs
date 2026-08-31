"""The process boundary: CommandError exits 1, UpstreamError 2, on stderr."""

from __future__ import annotations

import argparse

from btm_corekit import CommandError, UpstreamError, run_cli


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
