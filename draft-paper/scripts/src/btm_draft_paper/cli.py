"""Argument surface for the draft-paper trace tooling."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from btm_corekit import emit, run_cli
from btm_draft_paper.trace import verify


def cmd_trace_verify(args: argparse.Namespace) -> int:
    emit(verify(args.run_dir))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="btm-draft-paper")
    sub = parser.add_subparsers(dest="command", required=True)
    trace = sub.add_parser("trace", help="the run's append-only event log")
    trace_sub = trace.add_subparsers(dest="trace_command", required=True)
    verify_cmd = trace_sub.add_parser("verify", help="check TRACE.jsonl")
    verify_cmd.add_argument("run_dir", type=Path, help="run directory")
    verify_cmd.set_defaults(func=cmd_trace_verify)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
