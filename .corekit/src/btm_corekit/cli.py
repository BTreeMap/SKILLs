"""The process boundary shared by argparse-driven members: dispatch, batch
input, the rejection envelope, and the pad and clean subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, NoReturn, Protocol, TypeAlias

from btm_corekit.records.models import M, parse_model
from btm_corekit.report.channels import emit, signal
from btm_corekit.report.errors import CommandError, UpstreamError
from btm_corekit.report.verdicts import Diagnostic
from btm_corekit.store.pad import jot, pad_body, recall
from btm_corekit.store.sessions import SessionStore

REJECT_NEXT = "apply every fix above, then resend; --file makes the retry one edit"
PAD_SCHEMA = (
    "jot reads the entry from stdin or --file and stores any JSON object "
    "unchecked; recall filters by "
    '--kind/--match/--since/--limit; suggested body: {"kind": "...", ...}'
)
REFS_SCHEMA = "a ref is the kw slug, a full id, or any unique keyword subset"


ARGV_MESSAGE_MAX = 200


def bounded(message: str) -> str:
    """argparse echoes a malformed token back whole; slicing here is C-level,
    so the tail just names the size instead of spending it."""
    if len(message) <= ARGV_MESSAGE_MAX:
        return message
    return (
        f"{message[:ARGV_MESSAGE_MAX]}... [{len(message)} chars] "
        "free-form content belongs on stdin, not in an argument"
    )


class Parser(argparse.ArgumentParser):
    """argv, decoded like every other untrusted input. Stock argparse exits 2
    on a malformed line, but here 2 means retry-worthy; raising instead
    routes it through `CommandError`, and `add_subparsers` propagates this
    class to every subparser."""

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
    """Parse argv and dispatch to the subcommand's `func`. With `Parser`, a
    malformed argument line is a located rejection like any other, not
    argparse's own exit 2."""

    def parsed() -> int:
        args = parser.parse_args(argv)
        run: Callable[[argparse.Namespace], int] = args.func
        return run(args)

    return dispatch(parsed)


AT = "@"
STDIN = "-"


def text_source(raw: str) -> str:
    """A free-form value written inline, as `@path`, or as `-` for stdin.

    `@` marks a path only where a literal is also possible, so a parameter
    that takes nothing but a path keeps its bare spelling. `@@` starts a
    literal that begins with `@`.
    """
    if raw == STDIN:
        return sys.stdin.read()
    if raw.startswith(AT * 2):
        return raw[1:]
    if not raw.startswith(AT):
        return raw
    path = Path(raw[1:]).expanduser()
    try:
        return path.read_text(encoding="utf-8")
    except OSError as err:
        raise CommandError(f"cannot read {path}: {err}") from err


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
    """Exactly one place a payload comes from; supplying both an inline
    argument and `--file` is a rejection."""
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
    """What one subcommand calls its JSON, and which spellings it accepts; an
    empty-payload rejection never advertises a spelling the subcommand
    lacks."""

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
    """One JSON object from the batch's sole source; unparsable JSON becomes
    a located rejection, in the same envelope as any other."""
    raw = read_payload(sole_source(inline, file), BATCH)
    try:
        batch = json.loads(raw)
    except json.JSONDecodeError as err:
        return Diagnostic("$", f"make the batch valid JSON: {err}")
    if not isinstance(batch, dict):
        raise CommandError("the batch is one JSON object")
    return batch


def content(model: type[M], file: str | None, what: str) -> M:
    """A subcommand's free-form fields, as one JSON object from stdin or a
    file. Free-form text never travels in argv: the shell rewrites quotes,
    backslashes, and braces before the process ever sees them."""
    raw = read_payload(sole_source(None, file), CONTENT)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        raise CommandError(f"make {what} valid JSON: {err}") from err
    if not isinstance(data, dict):
        raise CommandError(f"{what} is one JSON object")
    return parse_model(model, data, what)


class View(StrEnum):
    """How much of a derived document to emit. A chain, not flags: each level
    is a superset of the one before, so asking for more never costs
    information. `plan`, the mid-session view, runs an order of magnitude
    smaller than the prose it omits; `draft` is the default."""

    PLAN = "plan"
    DRAFT = "draft"
    FULL = "full"

    @property
    def rank(self) -> int:
        return VIEW_ORDER.index(self)

    def covers(self, level: View) -> bool:
        """The chain law, and the only test a document builder needs. A
        richer view may add fields inside a row already emitted, but may
        never rewrite a value or drop a record: a caller can trust what a
        cheaper view already told it."""
        return self.rank >= level.rank


VIEW_ORDER: Final = (View.PLAN, View.DRAFT, View.FULL)


def wire_view(parser: argparse.ArgumentParser, omitted: str) -> None:
    """One spelling of "how much", identical in every member. `omitted` names
    what `plan` leaves out, since only the member knows."""
    parser.add_argument(
        "--view",
        type=View,
        choices=list(View),
        default=View.DRAFT,
        help=f"plan omits {omitted}; draft is the default; full adds the record dump",
    )


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
    """The gate protocol, defined once. Parse the batch, run the member's
    expansion, surface advisories, refuse with every problem in one verdict,
    and commit only when none remain. A contract that drifts between skills
    is the one thing an agent cannot discover."""
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
    # argparse's ambiguous shape, and a JSON body is what the shell mangles.
    jotter.add_argument(
        "--file", default=None, help="read the entry from this file instead of stdin"
    )
    jotter.add_argument("--text", action="store_true", help="store the entry as prose")
    recaller = commands.add_parser("recall", help="filtered slice of the pad")
    recaller.set_defaults(func=cmd_recall)
    recaller.add_argument("session", help="session identifier or directory")
    recaller.add_argument("--kind")
    recaller.add_argument("--match", type=text_source)
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
