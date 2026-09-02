"""The process boundary shared by argparse-driven members: dispatch, batch
input, the rejection envelope, and the pad and clean subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from btm_corekit.channels import emit, signal
from btm_corekit.errors import CommandError, UpstreamError
from btm_corekit.pad import jot, pad_body, recall
from btm_corekit.sessions import SessionStore
from btm_corekit.verdicts import Diagnostic

REJECT_NEXT = "apply every fix above, then resend; --file makes the retry one edit"
PAD_SCHEMA = (
    "jot stores any JSON object unchecked; recall filters by "
    '--kind/--match/--since/--limit; suggested body: {"kind": "...", ...}'
)
REFS_SCHEMA = "a ref is the kw slug, a full id, or any unique keyword subset"


def run_cli(parser: argparse.ArgumentParser, argv: Sequence[str] | None = None) -> int:
    """Dispatch to the parsed `func`: CommandError exits 1, UpstreamError 2."""
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UpstreamError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    except CommandError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


def read_batch(file: str | None) -> dict[str, Any] | Diagnostic:
    """One JSON object from --file or stdin; unparsable JSON is a located
    rejection, so the caller emits it in the same envelope as any other."""
    raw = Path(file).read_text(encoding="utf-8") if file else sys.stdin.read()
    if not raw.strip():
        raise CommandError("the batch is read from stdin or --file; both are empty")
    try:
        batch = json.loads(raw)
    except json.JSONDecodeError as err:
        return Diagnostic("$", f"make the batch valid JSON: {err}")
    if not isinstance(batch, dict):
        raise CommandError("the batch is one JSON object")
    return batch


def rejection(problems: Iterable[Diagnostic], store: str) -> dict[str, Any]:
    """The verdict a rejected batch returns: every fix, and what stayed put."""
    return {
        "rejected": [problem.view() for problem in problems],
        "unchanged": store,
        "next": REJECT_NEXT,
    }


def advise(lines: Iterable[str]) -> None:
    for line in lines:
        signal(line)


DirectoryOf = Callable[[argparse.Namespace], Path]
OnJot = Callable[[argparse.Namespace, dict[str, Any]], None]


def wire_pad(
    commands: argparse._SubParsersAction,
    directory_of: DirectoryOf,
    *,
    lore: str | None = None,
    on_jot: OnJot | None = None,
) -> None:
    """Add `jot` and `recall`; `lore` names the help of an optional --lore
    flag the member's directory_of honours; `on_jot` emits advisories."""

    def cmd_jot(args: argparse.Namespace) -> int:
        directory = directory_of(args)
        body, advisory = pad_body(args.entry, args.text)
        if advisory:
            signal(advisory)
        if on_jot is not None:
            on_jot(args, body)
        emit(jot(directory, body))
        return 0

    def cmd_recall(args: argparse.Namespace) -> int:
        emit(
            recall(
                directory_of(args),
                kind=args.kind,
                match=args.match,
                since=args.since,
                limit=args.limit,
            )
        )
        return 0

    jotter = commands.add_parser("jot", help="free note on the session pad")
    jotter.set_defaults(func=cmd_jot)
    jotter.add_argument("session", help="session identifier or directory")
    jotter.add_argument("entry", help="a JSON object, or prose with --text")
    jotter.add_argument("--text", action="store_true", help="store the entry as prose")
    recaller = commands.add_parser("recall", help="filtered slice of the pad")
    recaller.set_defaults(func=cmd_recall)
    recaller.add_argument("session", help="session identifier or directory")
    recaller.add_argument("--kind")
    recaller.add_argument("--match")
    recaller.add_argument("--since", help="entries after this pad id")
    recaller.add_argument("--limit", type=int)
    if lore is not None:
        for parser in (jotter, recaller):
            parser.add_argument("--lore", action="store_true", help=lore)


def wire_clean(commands: argparse._SubParsersAction, store: SessionStore) -> None:
    def cmd_clean(args: argparse.Namespace) -> int:
        emit(store.clean(args.session, args.all))
        return 0

    clean = commands.add_parser(
        "clean", help="list sessions with sizes; remove one or --all"
    )
    clean.set_defaults(func=cmd_clean)
    clean.add_argument("session", nargs="?")
    clean.add_argument("--all", action="store_true")
