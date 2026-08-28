"""Argument surface and the process boundary that turns failures into exit 1."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import btm_lit_review
from btm_corekit import run_cli
from btm_lit_review.constants import (
    DEFAULT_LIMIT,
    DIRECTIONS,
    SOURCES,
    STATUSES,
)
from btm_lit_review.curate import cmd_show, cmd_status, cmd_update
from btm_lit_review.gather import cmd_init, cmd_search, cmd_snowball
from btm_lit_review.session import cmd_clean
from btm_lit_review.verify import cmd_verify


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "session",
        help="session identifier (kept under the XDG state root) or directory",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="btm-lit-review",
        description=btm_lit_review.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a review session")
    add_common(init)
    init.add_argument("--question", required=True, help="the research question")
    init.add_argument("--level", choices=("lite", "full", "ultra"), default="full")
    init.set_defaults(func=cmd_init)

    search = commands.add_parser("search", help="run one logged search")
    add_common(search)
    search.add_argument("--source", choices=SOURCES, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    search.add_argument("--from-year", type=int, default=None)
    search.add_argument("--to-year", type=int, default=None)
    search.set_defaults(func=cmd_search)

    snowball = commands.add_parser(
        "snowball", help="follow citations of a corpus paper via OpenAlex"
    )
    add_common(snowball)
    snowball.add_argument("--seed", required=True, help="paper key, DOI, or arXiv id")
    snowball.add_argument("--direction", choices=DIRECTIONS, required=True)
    snowball.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    snowball.set_defaults(func=cmd_snowball)

    show = commands.add_parser("show", help="print papers for screening")
    add_common(show)
    show.add_argument("--status", choices=STATUSES, default="candidate")
    show.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    show.set_defaults(func=cmd_show)

    update = commands.add_parser(
        "update",
        help='apply screening decisions; stdin JSON: {"<key>": {"status": ...,'
        ' "reason": ..., "read_level": ...}}',
    )
    add_common(update)
    update.set_defaults(func=cmd_update)

    status = commands.add_parser("status", help="session counts and advisories")
    add_common(status)
    status.set_defaults(func=cmd_status)

    verify = commands.add_parser("verify", help="check DOIs of included papers")
    add_common(verify)
    verify.set_defaults(func=cmd_verify)

    clean = commands.add_parser(
        "clean", help="list sessions, or remove one (or --all) and free the space"
    )
    clean.add_argument("session", nargs="?", help="session name or directory")
    clean.add_argument("--all", action="store_true")
    clean.set_defaults(func=cmd_clean)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)


if __name__ == "__main__":
    sys.exit(main())
