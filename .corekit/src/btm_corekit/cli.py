"""The process boundary shared by argparse-driven members: dispatch, batch
input, the rejection envelope, and the pad and clean subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, Protocol, TypeAlias

from btm_corekit.channels import emit, signal
from btm_corekit.errors import CommandError, UpstreamError
from btm_corekit.models import M, parse_model
from btm_corekit.pad import jot, pad_body, recall
from btm_corekit.sessions import SessionStore
from btm_corekit.verdicts import Diagnostic

REJECT_NEXT = "apply every fix above, then resend; --file makes the retry one edit"
PAD_SCHEMA = (
    "jot reads the entry from stdin or --file and stores any JSON object "
    "unchecked; recall filters by "
    '--kind/--match/--since/--limit; suggested body: {"kind": "...", ...}'
)
REFS_SCHEMA = "a ref is the kw slug, a full id, or any unique keyword subset"


ARGV_MESSAGE_MAX = 200


def bounded(message: str) -> str:
    """argparse quotes the offending token verbatim, so a payload that reached
    argv by mistake would be echoed back whole. Slicing is C-level; the tail
    names the size instead of spending it."""
    if len(message) <= ARGV_MESSAGE_MAX:
        return message
    return (
        f"{message[:ARGV_MESSAGE_MAX]}... [{len(message)} chars] "
        "free-form content belongs on stdin, not in an argument"
    )


class Parser(argparse.ArgumentParser):
    """argv, decoded like every other untrusted input.

    Stock argparse exits 2 on a malformed argument line. In this library 2
    means the upstream failed and the call is worth retrying, so an agent
    obeying the exit contract would retry a call that can never succeed.
    Raising instead routes argv through the same `CommandError` channel as a
    bad batch, and `add_subparsers` propagates this class to every subparser.
    """

    def error(self, message: str) -> NoReturn:
        raise CommandError(bounded(message))


def dispatch(run: Callable[[], int]) -> int:
    """The exit contract, applied to one thunk: 0 done, 1 fix the input and
    resend, 2 upstream failed and the call is worth retrying. Every entry
    point routes through here, so no member can drift its own mapping."""
    try:
        return run()
    except UpstreamError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    except CommandError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


def run_cli(parser: argparse.ArgumentParser, argv: Sequence[str] | None = None) -> int:
    """Parse argv and dispatch to the subcommand's `func` under the contract.
    Parsing sits inside the boundary: with `Parser`, a malformed argument line
    is a located rejection like any other, not argparse's own exit 2."""

    def parsed() -> int:
        args = parser.parse_args(argv)
        run: Callable[[argparse.Namespace], int] = args.func
        return run(args)

    return dispatch(parsed)


@dataclass(frozen=True, slots=True)
class Inline:
    text: str


@dataclass(frozen=True, slots=True)
class FromFile:
    path: Path


@dataclass(frozen=True, slots=True)
class FromStdin:
    pass


Source = Inline | FromFile | FromStdin


def sole_source(inline: str | None, file: str | None) -> Source:
    """Exactly one place a payload comes from, parsed out of the two optional
    arguments argparse can hand over. The name is the law: supplying both an
    inline argument and `--file` is a rejection, where the earlier
    two-nullable shape resolved it silently and dropped the file."""
    match (inline, file):
        case (None, None):
            return FromStdin()
        case (None, str() as path):
            return FromFile(Path(path))
        case (str() as text, None):
            return Inline(text)
        case _:
            raise CommandError(
                "the payload came from an inline argument and --file; give one"
            )


@dataclass(frozen=True, slots=True)
class Payload:
    """What one subcommand calls its JSON and which spellings it accepts.
    Declared beside the parser that wires them rather than derived from
    whichever source happened to be used, so an empty-payload rejection can
    never advertise a spelling the subcommand does not have."""

    what: str
    spellings: str


BATCH = Payload("the batch", "stdin or --file")
ENTRY = Payload("the entry", "stdin or --file")
CONTENT = Payload("the content", "stdin or --file")


def read_payload(source: Source, kind: Payload) -> str:
    """Total over the three variants; empty from the chosen source rejects."""
    match source:
        case Inline(text):
            raw = text
        case FromFile(path):
            raw = path.read_text(encoding="utf-8")
        case FromStdin():
            raw = sys.stdin.read()
    if not raw.strip():
        raise CommandError(f"{kind.what} is read from {kind.spellings}; all are empty")
    return raw


def read_batch(
    file: str | None, inline: str | None = None
) -> dict[str, Any] | Diagnostic:
    """One JSON object from the batch's sole source; unparsable JSON is a
    located rejection, so the caller emits it in the same envelope as any
    other."""
    raw = read_payload(sole_source(inline, file), BATCH)
    try:
        batch = json.loads(raw)
    except json.JSONDecodeError as err:
        return Diagnostic("$", f"make the batch valid JSON: {err}")
    if not isinstance(batch, dict):
        raise CommandError("the batch is one JSON object")
    return batch


def content(model: type[M], file: str | None, what: str) -> M:
    """A subcommand's free-form fields, as one JSON object from stdin or a file.

    Free-form text never travels in argv: a research question, a fielded query
    such as `all:"phrase"`, and a regex all carry quotes, backslashes and
    braces that the shell rewrites before the process sees them, and a
    mis-quoted argument costs a whole tool call to discover. One object, one
    decode, every located problem in one verdict."""
    raw = read_payload(sole_source(None, file), CONTENT)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        raise CommandError(f"make {what} valid JSON: {err}") from err
    if not isinstance(data, dict):
        raise CommandError(f"{what} is one JSON object")
    return parse_model(model, data, what)


class Outcome(Protocol):
    """What any batch expansion returns. Structural, so a member's own result
    record satisfies it without inheriting anything."""

    advisories: list[str]
    problems: list[Diagnostic]


def gated(
    file: str | None,
    store: str,
    expand: Callable[[dict[str, Any]], Outcome],
    commit: Callable[[Any], dict[str, Any]],
) -> int:
    """The gate protocol, defined once.

    Parse the batch, run the member's expansion, surface advisories, refuse
    with every problem in one verdict, and commit only when none remain. Each
    member had its own copy; a copy that drifts makes the contract differ
    between skills, which is the one thing an agent cannot discover."""
    batch = read_batch(file)
    if isinstance(batch, Diagnostic):
        emit(rejection([batch], store))
        return 1
    result = expand(batch)
    advise(result.advisories)
    if result.problems:
        emit(rejection(result.problems, store))
        return 1
    emit(commit(result))
    return 0


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


# Invariant in its parser type, so the alias names the decoding parser: every
# member builds one, and a stock ArgumentParser would skip the argv boundary.
Commands: TypeAlias = "argparse._SubParsersAction[Parser]"

DirectoryOf = Callable[[argparse.Namespace], Path]
OnJot = Callable[[argparse.Namespace, dict[str, Any]], None]


def wire_pad(
    commands: Commands,
    directory_of: DirectoryOf,
    *,
    lore: str | None = None,
    on_jot: OnJot | None = None,
) -> None:
    """Add `jot` and `recall`; `lore` names the help of an optional --lore
    flag the member's directory_of honours; `on_jot` emits advisories."""

    def cmd_jot(args: argparse.Namespace) -> int:
        directory = directory_of(args)
        body, advisory = pad_body(
            read_payload(sole_source(None, args.file), ENTRY), args.text
        )
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
    # No inline positional: an optional positional interleaved with flags is
    # argparse's ambiguous shape, and a JSON body is exactly what the shell
    # mangles. The entry arrives on stdin or from --file.
    jotter.add_argument(
        "--file", default=None, help="read the entry from this file instead of stdin"
    )
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


def wire_clean(commands: Commands, store: SessionStore) -> None:
    def cmd_clean(args: argparse.Namespace) -> int:
        emit(store.clean(args.session, args.all))
        return 0

    clean = commands.add_parser(
        "clean", help="list sessions with sizes; remove one or --all"
    )
    clean.set_defaults(func=cmd_clean)
    clean.add_argument("session", nargs="?")
    clean.add_argument("--all", action="store_true")
