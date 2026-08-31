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
from btm_lit_review.curate import SORTS, cmd_screen, cmd_show, cmd_status, cmd_update
from btm_lit_review.draft import cmd_cite_check
from btm_lit_review.gather import cmd_init, cmd_search, cmd_snowball
from btm_lit_review.notebook import cmd_note
from btm_lit_review.session import cmd_clean
from btm_lit_review.verify import cmd_verify
from btm_lit_review.views import cmd_brief, cmd_jot, cmd_recall, cmd_schema

MATCH_FIELDS = ("title", "abstract", "venue")


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "session",
        help="session identifier (kept under the XDG state root) or directory",
    )


def wire_gather(commands: argparse._SubParsersAction) -> None:
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


def wire_curate(commands: argparse._SubParsersAction) -> None:
    screen = commands.add_parser(
        "screen", help="apply one regex rule to every candidate, recorded as bulk"
    )
    add_common(screen)
    screen.add_argument("--on", choices=MATCH_FIELDS, default="title")
    screen.add_argument("--match", required=True, help="case-insensitive regex")
    verdict = screen.add_mutually_exclusive_group(required=True)
    verdict.add_argument("--exclude", action="store_true")
    verdict.add_argument("--include", action="store_true")
    screen.add_argument("--reason", required=True)
    screen.set_defaults(func=cmd_screen)

    show = commands.add_parser("show", help="project the corpus for screening")
    add_common(show)
    show.add_argument("--status", choices=STATUSES, default="candidate")
    show.add_argument("--keys", help="comma-separated keys; overrides --status")
    show.add_argument("--match", help="case-insensitive regex filter")
    show.add_argument("--on", choices=MATCH_FIELDS, default="title")
    show.add_argument("--fields", help="comma-separated paper fields to project")
    show.add_argument("--sort", choices=tuple(SORTS), default="citations")
    show.add_argument("--format", choices=("json", "tsv"), default="json")
    show.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    show.set_defaults(func=cmd_show)

    update = commands.add_parser(
        "update",
        help='apply screening decisions; stdin JSON: {"<key>": {"status": ...,'
        ' "reason": ..., "read_level": ...}}',
    )
    add_common(update)
    update.set_defaults(func=cmd_update)


def wire_notebook(commands: argparse._SubParsersAction) -> None:
    note = commands.add_parser("note", help="admit findings and gaps into the notebook")
    add_common(note)
    note.add_argument(
        "--file",
        default=None,
        help="read the batch from this file; retries cost one edit",
    )
    note.set_defaults(func=cmd_note)

    jotter = commands.add_parser("jot", help="free note on the session pad")
    add_common(jotter)
    jotter.add_argument("entry", help="a JSON object, or prose with --text")
    jotter.add_argument("--text", action="store_true", help="store the entry as prose")
    jotter.add_argument(
        "--lore", action="store_true", help="write to the cross-session tool pad"
    )
    jotter.set_defaults(func=cmd_jot)

    recaller = commands.add_parser("recall", help="filtered slice of the pad")
    add_common(recaller)
    recaller.add_argument("--kind")
    recaller.add_argument("--match")
    recaller.add_argument("--since", help="entries after this pad id")
    recaller.add_argument("--limit", type=int)
    recaller.add_argument(
        "--lore", action="store_true", help="read the cross-session tool pad"
    )
    recaller.set_defaults(func=cmd_recall)

    brief = commands.add_parser(
        "brief", help="resume view: findings, gaps, drift, markers, pad tail"
    )
    add_common(brief)
    brief.set_defaults(func=cmd_brief)

    cite = commands.add_parser(
        "cite-check", help="check every [n] in a draft against the corpus"
    )
    add_common(cite)
    cite.add_argument("--draft", required=True, help="path to the draft file")
    cite.set_defaults(func=cmd_cite_check)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="btm-lit-review",
        description=btm_lit_review.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    wire_gather(commands)
    wire_curate(commands)
    wire_notebook(commands)

    schema = commands.add_parser("schema", help="print every record shape")
    schema.set_defaults(func=cmd_schema)

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
