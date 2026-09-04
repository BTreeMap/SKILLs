"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

import btm_ponder
from btm_corekit import (
    JSON,
    PAD_SCHEMA,
    REFS_SCHEMA,
    Model,
    NonEmpty,
    Parser,
    View,
    content,
    dump,
    emit,
    gated,
    mint,
    now_iso,
    pad_ids,
    run_cli,
    signal,
    wire_clean,
    wire_pad,
    wire_view,
)
from btm_ponder.batch import BATCH_KEYS, SCHEMA, NoteResult, expand_batch
from btm_ponder.ledger import replay
from btm_ponder.state import MODES, Mode, Open
from btm_ponder.store import (
    STORE,
    SessionMeta,
    event_log,
    orient,
    read_events,
    read_meta,
    write_meta,
)
from btm_ponder.views import (
    INFORMAL_DEMOTED,
    counts_of,
    hedges,
    leaf_view,
    marker_table,
    scaffold,
    sections,
    violations,
    yield_table,
)


class Framing(Model):
    """What one session is about. Prose, so it arrives on stdin rather than
    through argv, where a question mark and an apostrophe are shell syntax."""

    question: NonEmpty
    focus: str | None = None


def cmd_init(args: argparse.Namespace) -> int:
    framing = content(Framing, args.file, "the framing")  # before the mkdir:
    made = STORE.create(args.ref)  # a refused framing leaves no empty session
    meta = SessionMeta(
        question=framing.question,
        focus=framing.focus,
        mode=args.mode,
        created=now_iso(),
    )
    write_meta(made.directory, meta)
    emit({"session": made.name, "dir": str(made.directory), **dump(meta)})
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    directory = STORE.directory(args.session)
    events = read_events(directory)
    ledger = replay(events)

    def expand(batch: dict[str, Any]) -> NoteResult:
        return expand_batch(ledger, batch, mint, pad_ids(directory))

    def commit(result: NoteResult) -> dict[str, Any]:
        event_log(directory).append(result.events, held=len(events))
        document: dict[str, JSON] = {
            "session": directory.name,
            "admitted": dict(Counter(event["e"] for event in result.events)),
            "counts": counts_of(ledger),
            "open": [
                leaf_id
                for leaf_id, leaf in ledger.leaves.items()
                if isinstance(leaf.state, Open)
            ],
            "yield": yield_table(events + result.events),
        }
        if args.view.covers(View.DRAFT):
            # Only a later batch referencing these ids needs them; a round that
            # mints and consumes in one batch pays 2.5 KB for nothing.
            document["minted"] = result.minted
        if result.merged:
            document["merged"] = result.merged
        if args.view.covers(View.FULL):
            document["leaves"] = {
                leaf_id: {"question": leaf.question, **leaf_view(leaf.state)}
                for leaf_id, leaf in ledger.leaves.items()
            }
        return document

    return gated(args.file, "ledger", expand, commit)


def cmd_check(args: argparse.Namespace) -> int:
    directory = STORE.directory(args.session)
    events = read_events(directory)
    ledger = replay(events)
    meta = read_meta(directory)
    mode = meta.mode
    markers = {
        source_id: f"S{index}"
        for index, source_id in enumerate(ledger.source_order, start=1)
    }
    found = violations(ledger)
    demoted = (
        [line for line in found if line.startswith(INFORMAL_DEMOTED)]
        if mode is Mode.INFORMAL
        else []
    )
    blocking = [line for line in found if line not in demoted]
    if blocking:
        signal(f"{len(blocking)} violation(s); details in the JSON violations array")
    signal("Boundary section is yours: render it where the answer flips inside scope")
    document: dict[str, JSON] = {
        "session": directory.name,
        "mode": mode,
        "question": meta.question,
        "sections": sections(ledger),
        # Scaffold before markers: a draft is written from the scaffold and
        # only consults the marker table to render its Sources section, so the
        # long table sitting first cost a second read of the whole document.
        "scaffold": scaffold(ledger, markers, args.view),
        "violations": blocking,
        "advisories": demoted,
        "hedges": hedges(ledger),
        "yield": yield_table(events),
    }
    if args.view.covers(View.DRAFT):
        document["markers"] = marker_table(ledger, markers)
    if args.view.covers(View.FULL):
        document["leaves"] = {
            leaf_id: {"question": leaf.question, **leaf_view(leaf.state)}
            for leaf_id, leaf in ledger.leaves.items()
        }
    emit(document)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    emit(orient(STORE.directory(args.session)))
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    emit(
        {
            "note_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
            "order": "leaves, sources, closes, sweeps, checkpoints; later entries "
            "may reference ids minted earlier in the same batch",
            "refs": REFS_SCHEMA + "; receipts echo every minted id",
            "pad": PAD_SCHEMA + "; suggested kinds: quote, hunch, open",
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_ponder.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser(
        "init",
        help='mint a session; {"question": ..., "focus": ...} on stdin or --file',
    )
    init.set_defaults(func=cmd_init)
    init.add_argument("ref", help="two or three keywords, or a directory path")
    init.add_argument(
        "--file", default=None, help="read the framing from this file instead of stdin"
    )
    init.add_argument(
        "--mode",
        choices=MODES,
        default="full",
        help="informal demotes draft blockers to advisories",
    )
    note = commands.add_parser(
        "note", help="admit one round of leaves, sources, and closes"
    )
    note.set_defaults(func=cmd_note)
    note.add_argument("session", help="session identifier; batch JSON on stdin")
    note.add_argument(
        "--file",
        default=None,
        help="read the batch from this file; retries cost one edit",
    )
    wire_view(note, "the minted-id table")
    check = commands.add_parser(
        "check", help="derive the drafting scaffold and any violations"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("session", help="session identifier")
    wire_view(check, "the stored prose and the source table")
    status = commands.add_parser(
        "status", help="counts, open leaves, and the next step"
    )
    status.set_defaults(func=cmd_status)
    status.add_argument("session", help="session identifier")
    schema = commands.add_parser("schema", help="print the note batch shape")
    schema.set_defaults(func=cmd_schema)
    wire_pad(commands, lambda args: STORE.directory(args.session))
    wire_clean(commands, STORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
