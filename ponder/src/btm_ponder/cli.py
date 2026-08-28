"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import btm_ponder
from btm_corekit import (
    Ambiguous,
    CommandError,
    Exact,
    NoMatch,
    Recovered,
    band_signal,
    is_pathlike,
    mint,
    resolve,
    tree_bytes,
)
from btm_ponder.batch import expand_batch
from btm_ponder.ledger import apply, replay
from btm_ponder.report import emit, signal
from btm_ponder.state import Open, require
from btm_ponder.store import (
    append_events,
    ledger_path,
    orient,
    read_events,
    read_meta,
    session_dir,
    session_ids,
    sessions_root,
    write_meta,
)
from btm_ponder.views import (
    counts_of,
    hedges,
    leaf_view,
    sections,
    violations,
    yield_table,
)


def create_session(directory: Path, name: str, args: argparse.Namespace) -> int:
    meta = {
        "question": args.question,
        "focus": args.focus,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_meta(directory, meta)
    emit({"session": name, **meta})
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    ref = args.ref
    if is_pathlike(ref):
        directory = Path(ref).expanduser()
        if not args.question:
            require(
                ledger_path(directory).exists(),
                f"no session at {directory}; pass --question to create one",
            )
            emit(orient(directory))
            return 0
        require(
            not ledger_path(directory).exists(),
            f"session already exists at {directory}",
        )
        return create_session(directory, str(directory), args)
    match resolve(ref, session_ids()):
        case Exact(sid):
            emit(orient(sessions_root() / sid))
        case Recovered(sid):
            signal(f"recovered session '{ref}' -> {sid}; use the full identifier")
            emit(orient(sessions_root() / sid))
        case Ambiguous(candidates):
            raise CommandError(
                f"'{ref}' is ambiguous across sessions: {', '.join(candidates)}"
            )
        case NoMatch():
            require(
                bool(args.question),
                f"no session matches '{ref}'; pass --question to create one",
            )
            full = mint(ref.split())
            if advice := band_signal(full.rsplit("-", 1)[0]):
                signal(advice)
            return create_session(sessions_root() / full, full, args)
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    raw = sys.stdin.read()
    require(bool(raw.strip()), "note reads the JSON batch from stdin")
    batch = json.loads(raw)
    require(isinstance(batch, dict), "note takes one JSON object")
    events = read_events(directory)
    ledger = replay(events)
    expanded, minted, advisories = expand_batch(ledger, batch, mint)
    for event in expanded:
        apply(ledger, event)
    append_events(directory, expanded)
    for line in advisories:
        signal(line)
    emit(
        {
            "session": directory.name,
            "minted": minted,
            "counts": counts_of(ledger),
            "open": [
                leaf_id
                for leaf_id, leaf in ledger.leaves.items()
                if isinstance(leaf.state, Open)
            ],
            "yield": yield_table(events + expanded),
        }
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    events = read_events(directory)
    ledger = replay(events)
    markers = {
        source_id: f"S{index}"
        for index, source_id in enumerate(ledger.source_order, start=1)
    }
    found = violations(ledger)
    for line in found:
        signal(line)
    signal("Boundary section is yours: render it where the answer flips inside scope")
    emit(
        {
            "session": directory.name,
            "question": read_meta(directory).get("question"),
            "sections": sections(ledger),
            "violations": found,
            "hedges": hedges(ledger),
            "yield": yield_table(events),
            "sources": [
                {
                    "marker": markers[source_id],
                    "id": source_id,
                    "cls": ledger.sources[source_id].cls,
                    "title": ledger.sources[source_id].title,
                    "url": ledger.sources[source_id].url,
                    "leaf": ledger.sources[source_id].leaf,
                }
                for source_id in ledger.source_order
            ],
            "leaves": {
                leaf_id: {"question": leaf.question, **leaf_view(leaf.state)}
                for leaf_id, leaf in ledger.leaves.items()
            },
        }
    )
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    root = sessions_root()
    if args.all and args.session:
        raise CommandError("pass a session or --all, one of the two")
    if args.all:
        if not root.is_dir():
            emit({"removed": None, "bytes_freed": 0})
            return 0
        freed = tree_bytes(root)
        shutil.rmtree(root)
        emit({"removed": str(root), "bytes_freed": freed})
        return 0
    if args.session is None:
        listing = (
            [
                {"session": entry.name, "bytes": tree_bytes(entry)}
                for entry in sorted(root.iterdir())
                if entry.is_dir()
            ]
            if root.is_dir()
            else []
        )
        emit(
            {
                "sessions_root": str(root),
                "sessions": listing,
                "next": "pass a session identifier or --all to remove and free space",
            }
        )
        return 0
    target = session_dir(args.session)
    if not ledger_path(target).is_file():
        raise CommandError(
            f"{target} holds no session (ledger.jsonl absent); refusing to remove"
        )
    freed = tree_bytes(target)
    shutil.rmtree(target)
    emit({"removed": str(target), "bytes_freed": freed})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=btm_ponder.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    opener = commands.add_parser("open")
    opener.set_defaults(func=cmd_open)
    opener.add_argument("ref", help="two or three keywords in one quoted argument")
    opener.add_argument("--question")
    opener.add_argument("--focus", default=None)
    note = commands.add_parser("note")
    note.set_defaults(func=cmd_note)
    note.add_argument("session", help="session identifier; batch JSON on stdin")
    check = commands.add_parser("check")
    check.set_defaults(func=cmd_check)
    check.add_argument("session", help="session identifier")
    clean = commands.add_parser("clean")
    clean.set_defaults(func=cmd_clean)
    clean.add_argument("session", nargs="?")
    clean.add_argument("--all", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
