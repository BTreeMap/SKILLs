"""The process boundary shared by argparse-driven members: dispatch, content
slots, the rejection envelope, and the pad and clean subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, NoReturn, Protocol, TypeAlias, overload
from weakref import WeakKeyDictionary

from btm_corekit.records.models import M, parse_model
from btm_corekit.report.channels import emit, signal
from btm_corekit.report.errors import CommandError, UpstreamError
from btm_corekit.report.verdicts import Diagnostic
from btm_corekit.store.pad import jot, pad_body, recall
from btm_corekit.store.sessions import SessionStore

PAD_SCHEMA = (
    "jot stores any JSON object unchecked; recall filters by "
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
        "free-form content belongs on the pipe, not in an argument"
    )


def at_least_one(raw: str) -> int:
    """An argparse type for a count of things to fetch or show: below 1 asks
    for nothing, refused where it is written rather than floored into a call
    that ran and returned nothing."""
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a whole number") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"{value} asks for nothing; pass 1 or more")
    return value


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


@dataclass(frozen=True, slots=True)
class Inline:
    """The value itself, written in argv."""

    text: str


@dataclass(frozen=True, slots=True)
class FromFile:
    """A file the command opens. Files are shareable: two slots may name one."""

    path: Path


@dataclass(frozen=True, slots=True)
class FromStdin:
    """The process stream. Affine: one stream, so one slot holds it."""


Source = Inline | FromFile | FromStdin


@dataclass(frozen=True, slots=True)
class Required:
    """A slot the command cannot run without. Unclaimed, it reads the pipe."""

    name: str
    inline: bool = True


@dataclass(frozen=True, slots=True)
class Optional:
    """A slot that may go unfilled. Unclaimed, it stays absent."""

    name: str
    inline: bool = True


Slot = Required | Optional


class Provenance(StrEnum):
    """The qualifier after a slot's name in `--<slot>:<provenance>`. Closed,
    so a spelling added here reaches every generated family at once."""

    FILE = "file"
    STDIN = "stdin"


def dest_of(slot: Slot) -> str:
    """The slot's base argparse attribute. `:` is no identifier, so every
    generated flag names its dest outright."""
    return slot.name.replace("-", "_")


def flag(slot: Slot, of: Provenance | None = None) -> str:
    return f"--{slot.name}:{of}" if of else f"--{slot.name}"


def spellings(slot: Slot) -> str:
    """Every place this slot's bytes may come from, for its rejections."""
    ways = [flag(slot)] if slot.inline else []
    ways += [flag(slot, Provenance.FILE), flag(slot, Provenance.STDIN)]
    match slot:
        case Required():
            ways.append("the pipe")
        case Optional():
            pass
    return ", ".join(ways)


class Claim(argparse.Action):
    """One shared dest holds the name of the slot reading stdin, so a second
    claim is a rejection rather than argparse's silent last-wins."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        held = getattr(namespace, self.dest, None)
        if held is not None and held != self.const:
            parser.error(
                f"stdin is claimed by --{held}:{Provenance.STDIN}; "
                f"{option_string} wants it too"
            )
        setattr(namespace, self.dest, self.const)


# One required slot per parser, since they would both fall back to one stdin.
# Weak keys, so the bookkeeping dies with the parser and mutates nothing the
# kernel does not own.
REQUIRED_OF: Final[WeakKeyDictionary[argparse.ArgumentParser, str]] = (
    WeakKeyDictionary()
)


def add_slot(parser: argparse.ArgumentParser, slot: Slot, shape: str) -> None:
    """Generate a slot's whole flag family from one declaration, so no two
    slots drift apart. `shape` says what the content is."""
    match slot:
        case Required(name=name):
            held = REQUIRED_OF.setdefault(parser, name)
            if held != name:
                raise ValueError(
                    f"{parser.prog}: {held} and {name} both fall back to the pipe; "
                    "at most one required slot per command"
                )
        case Optional():
            pass
    dest = dest_of(slot)
    if slot.inline:
        parser.add_argument(flag(slot), dest=dest, help=shape)
    else:
        # Appended, so a second content slot documents its shape beside the
        # first instead of erasing it.
        described = f"{slot.name} from {spellings(slot)}: {shape}"
        parser.description = " ".join(filter(None, (parser.description, described)))
    parser.add_argument(
        flag(slot, Provenance.FILE),
        dest=f"{dest}_{Provenance.FILE}",
        type=Path,
        metavar="PATH",
        help=f"read the {slot.name} from PATH",
    )
    parser.add_argument(
        flag(slot, Provenance.STDIN),
        dest=Provenance.STDIN,
        action=Claim,
        nargs=0,
        const=slot.name,
        help=f"read the {slot.name} from the pipe",
    )


def claims(slot: Slot, args: argparse.Namespace) -> list[tuple[str, Source]]:
    """The slot's filled spellings, at most three, in flag order."""
    dest = dest_of(slot)
    found: list[tuple[str, Source]] = []
    written = getattr(args, dest, None) if slot.inline else None
    if written is not None:
        found.append((flag(slot), Inline(written)))
    path = getattr(args, f"{dest}_{Provenance.FILE}", None)
    if path is not None:
        found.append((flag(slot, Provenance.FILE), FromFile(path)))
    if getattr(args, Provenance.STDIN, None) == slot.name:
        found.append((flag(slot, Provenance.STDIN), FromStdin()))
    return found


def source_of(slot: Slot, args: argparse.Namespace) -> Source | None:
    """Exactly one provenance per slot; two is a rejection naming both."""
    match claims(slot, args):
        case []:
            return unclaimed(slot, args)
        case [(_, source)]:
            return source
        case given:
            names = " and ".join(name for name, _ in given)
            raise CommandError(f"the {slot.name} came from {names}; give one")


def unclaimed(slot: Slot, args: argparse.Namespace) -> Source | None:
    """What a slot no flag filled falls back to."""
    match slot:
        case Required(name=name):
            held = getattr(args, Provenance.STDIN, None)
            if held is not None:
                raise CommandError(
                    f"the {name} has no source: stdin is claimed by "
                    f"--{held}:{Provenance.STDIN}"
                )
            return FromStdin()
        case Optional():
            return None


def read_source(slot: Slot, source: Source) -> str:
    """Total over the three variants; empty from the chosen source rejects."""
    match source:
        case Inline(written):
            raw = written
        case FromFile(path):
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError as err:
                raise CommandError(f"cannot read {path}: {err}") from err
        case FromStdin():
            raw = sys.stdin.read()
    if not raw.strip():
        raise CommandError(f"the {slot.name} reads from {spellings(slot)}; all empty")
    return raw


@overload
def text(slot: Required, args: argparse.Namespace) -> str: ...


@overload
def text(slot: Optional, args: argparse.Namespace) -> str | None: ...


def text(slot: Slot, args: argparse.Namespace) -> str | None:
    """A slot's bytes. A required slot always yields; an unfilled optional
    slot yields None."""
    source = source_of(slot, args)
    return None if source is None else read_source(slot, source)


@dataclass(frozen=True, slots=True)
class Malformed:
    """Slot text that is no JSON object. `fix` is the imperative, so each
    caller routes one message through its own channel."""

    fix: str


def decoded(slot: Required, args: argparse.Namespace) -> dict[str, Any] | Malformed:
    """The slot's JSON object. Free-form text never travels in argv: the
    shell rewrites quotes, backslashes, and braces before the process ever
    sees them."""
    try:
        data = json.loads(text(slot, args))
    except json.JSONDecodeError as err:
        return Malformed(f"make the {slot.name} valid JSON: {err}")
    if not isinstance(data, dict):
        raise CommandError(f"the {slot.name} is one JSON object")
    return data


def read_batch(slot: Required, args: argparse.Namespace) -> dict[str, Any] | Diagnostic:
    """A batch for the gate; unparsable JSON becomes a located rejection, in
    the same envelope as any other."""
    match decoded(slot, args):
        case Malformed(fix):
            return Diagnostic("$", fix)
        case batch:
            return batch


def content(model: type[M], slot: Required, args: argparse.Namespace) -> M:
    """A subcommand's free-form fields, parsed into its record at once."""
    match decoded(slot, args):
        case Malformed(fix):
            raise CommandError(fix)
        case data:
            return parse_model(model, data, f"the {slot.name}")


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
    slot: Required,
    args: argparse.Namespace,
    store: str,
    expand: Callable[[dict[str, Any]], Outcome],
    commit: Callable[[Any], dict[str, Any]],
) -> int:
    """The gate protocol, defined once. Parse the batch, run the member's
    expansion, surface advisories, refuse with every problem in one verdict,
    and commit only when none remain. A contract that drifts between skills
    is the one thing an agent cannot discover."""
    batch = read_batch(slot, args)
    if isinstance(batch, Diagnostic):
        emit(rejection([batch], store, slot))
        return 1
    result = expand(batch)
    advise(result.advisories)
    if result.problems:
        emit(rejection(result.problems, store, slot))
        return 1
    emit(commit(result))
    return 0


def rejection(
    problems: Iterable[Diagnostic], store: str, slot: Required
) -> dict[str, Any]:
    """The verdict a rejected batch returns: every fix, and what stayed put."""
    return {
        "rejected": [problem.view() for problem in problems],
        "unchanged": store,
        "next": f"apply every fix above, then resend; "
        f"{flag(slot, Provenance.FILE)} makes the retry one edit",
    }


def advise(lines: Iterable[str]) -> None:
    for line in lines:
        signal(line)


# Invariant in its parser type, so the alias names the decoding parser: every
# member builds one, and a stock ArgumentParser would skip the argv boundary.
Commands: TypeAlias = "argparse._SubParsersAction[Parser]"

DirectoryOf = Callable[[argparse.Namespace], Path]
OnJot = Callable[[argparse.Namespace, dict[str, Any]], None]

# Slots every member spells the same way. A member declares only its own.
BATCH = Required("batch", inline=False)
ENTRY = Required("entry", inline=False)
MATCH = Optional("match")


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
        body, advisory = pad_body(text(ENTRY, args), args.prose)
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
                match=text(MATCH, args),
                since=args.since,
                limit=args.limit,
            )
        )
        return 0

    jotter = commands.add_parser("jot", help="free note on the session pad")
    jotter.set_defaults(func=cmd_jot)
    jotter.add_argument("session", help="session identifier or directory")
    add_slot(jotter, ENTRY, "any JSON object")
    jotter.add_argument("--prose", action="store_true", help="store the entry as prose")
    recaller = commands.add_parser("recall", help="filtered slice of the pad")
    recaller.set_defaults(func=cmd_recall)
    recaller.add_argument("session", help="session identifier or directory")
    recaller.add_argument("--kind")
    add_slot(recaller, MATCH, "case-insensitive regex over the entry")
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
