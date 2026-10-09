"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

import btm_ponder
from btm_corekit import (
    BATCH,
    JSON,
    PAD_SCHEMA,
    REFS_SCHEMA,
    EventLog,
    Model,
    NonEmpty,
    Parser,
    Required,
    View,
    add_slot,
    content,
    dump,
    emit,
    gated,
    make_id,
    now_iso,
    pad_ids,
    run_cli,
    signal,
    wire_cite,
    wire_clean,
    wire_pad,
    wire_project,
    wire_view,
)
from btm_ponder.batch import BATCH_KEYS, SCHEMA, RecordResult, expand_batch
from btm_ponder.ledger import replay
from btm_ponder.state import LEVELS, Level, Open
from btm_ponder.store import (
    LEDGER,
    STORE,
    SessionMeta,
    orient,
)
from btm_ponder.views import (
    LITE_DEMOTED,
    counts_of,
    hedges,
    leaf_view,
    mark_table,
    sections,
    structure,
    violations,
    yield_table,
)

FRAMING = Required("framing", inline=False)


class Framing(Model):
    """What one session is about. Prose, so it arrives as content rather than
    through argv, where a question mark and an apostrophe are shell syntax."""

    question: NonEmpty
    focus: str | None = None


def cmd_start(args: argparse.Namespace) -> int:
    framing = content(Framing, FRAMING, args)  # before the mkdir:
    made = STORE.create(args.ref)  # a refused framing leaves no empty session
    meta = SessionMeta(
        question=framing.question,
        focus=framing.focus,
        level=args.level,
        created=now_iso(),
        project=args.project,
    )
    STORE.write_meta(made.directory, meta)
    EventLog(made.directory / LEDGER).touch()
    emit({"session": made.name, "dir": str(made.directory), **dump(meta)})
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    directory = STORE.directory(args.session)
    log = EventLog(directory / LEDGER)
    events = log.read()
    ledger = replay(events)

    def expand(batch: dict[str, Any]) -> RecordResult:
        return expand_batch(ledger, batch, make_id, pad_ids(directory))

    def commit(result: RecordResult) -> dict[str, Any]:
        log.append(result.events, held=len(events))
        document: dict[str, JSON] = {
            "session": directory.name,
            "accepted": dict(Counter(event["e"] for event in result.events)),
            "counts": counts_of(ledger),
            "open": [
                leaf_id
                for leaf_id, leaf in ledger.leaves.items()
                if isinstance(leaf.status, Open)
            ],
            "yield": yield_table(events + result.events),
        }
        if args.view.covers(View.DRAFT):
            # Only a later batch referencing these ids needs them; a cycle that
            # makes and consumes in one batch pays 2.5 KB for nothing.
            document["new"] = result.new
        if result.merged:
            document["merged"] = result.merged
        if args.view.covers(View.FULL):
            document["leaves"] = {
                leaf_id: {"question": leaf.question, **leaf_view(leaf.status)}
                for leaf_id, leaf in ledger.leaves.items()
            }
        return document

    return gated(BATCH, args, "ledger", expand, commit)


def cmd_check(args: argparse.Namespace) -> int:
    directory = STORE.directory(args.session)
    events = EventLog(directory / LEDGER).read()
    ledger = replay(events)
    meta = STORE.read_meta(directory, SessionMeta)
    level = meta.level
    marks = {
        source_id: f"S{index}"
        for index, source_id in enumerate(ledger.source_order, start=1)
    }
    found = violations(ledger)
    demoted = (
        [line for line in found if line.startswith(LITE_DEMOTED)]
        if level is Level.LITE
        else []
    )
    blocking = [line for line in found if line not in demoted]
    if blocking:
        signal(f"{len(blocking)} violation(s); details in the JSON violations array")
    signal("Boundary section is yours: render it where the answer flips inside scope")
    document: dict[str, JSON] = {
        "session": directory.name,
        "level": level,
        "question": meta.question,
        "sections": sections(ledger),
        # Structure before marks: the mark table serves only the Sources
        # section, so putting it first would cost a second read to draft.
        "structure": structure(ledger, marks, args.view),
        "violations": blocking,
        "advisories": demoted,
        "hedges": hedges(ledger),
        "yield": yield_table(events),
    }
    if args.view.covers(View.DRAFT):
        document["marks"] = mark_table(ledger, marks)
    if args.view.covers(View.FULL):
        document["leaves"] = {
            leaf_id: {"question": leaf.question, **leaf_view(leaf.status)}
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
            "record_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
            "sequence": "leaves, sources, closes, scans, checkpoints; later entries "
            "may reference ids made earlier in the same batch",
            "refs": REFS_SCHEMA + "; receipts echo every new id",
            "pad": PAD_SCHEMA,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_ponder.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="make a session from one framing")
    start.set_defaults(func=cmd_start)
    start.add_argument("ref", help="two or three keywords, or a directory path")
    add_slot(start, FRAMING, '{"question": ..., "focus": ...}')
    start.add_argument(
        "--level",
        type=Level,
        choices=LEVELS,
        default=Level.FULL,
        help="lite demotes draft blockers to advisories",
    )
    wire_project(start)
    record = commands.add_parser(
        "record", help="accept one cycle of leaves, sources, and closes"
    )
    record.set_defaults(func=cmd_record)
    record.add_argument("session", help="session identifier")
    add_slot(record, BATCH, "leaves, sources, closes, scans, checkpoints")
    wire_view(record, "the new-id table")
    check = commands.add_parser(
        "check", help="derive the drafting structure and any violations"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("session", help="session identifier")
    wire_view(check, "the stored prose and the source table")
    status = commands.add_parser(
        "status", help="counts, open leaves, and the next step"
    )
    status.set_defaults(func=cmd_status)
    status.add_argument("session", help="session identifier")
    schema = commands.add_parser("schema", help="print the record batch shape")
    schema.set_defaults(func=cmd_schema)
    wire_pad(commands, STORE)
    wire_cite(commands, STORE.skill)
    wire_clean(commands, STORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
