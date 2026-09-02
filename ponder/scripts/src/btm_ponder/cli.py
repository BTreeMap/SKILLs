"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
from collections import Counter

import btm_ponder
from btm_corekit import (
    PAD_SCHEMA,
    REFS_SCHEMA,
    Diagnostic,
    advise,
    emit,
    mint,
    now_iso,
    pad_ids,
    read_batch,
    rejection,
    run_cli,
    signal,
    wire_clean,
    wire_pad,
)
from btm_ponder.batch import BATCH_KEYS, SCHEMA, expand_batch
from btm_ponder.ledger import replay
from btm_ponder.state import MODES, Open
from btm_ponder.store import (
    STORE,
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
    scaffold,
    sections,
    violations,
    yield_table,
)


def cmd_init(args: argparse.Namespace) -> int:
    made = STORE.create(args.ref)
    meta = {
        "question": args.question,
        "focus": args.focus,
        "mode": args.mode,
        "created": now_iso(),
    }
    write_meta(made.directory, meta)
    emit({"session": made.name, "dir": str(made.directory), **meta})
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    directory = STORE.directory(args.session)
    batch = read_batch(args.file)
    if isinstance(batch, Diagnostic):
        emit(rejection([batch], "ledger"))
        return 1
    events = read_events(directory)
    ledger = replay(events)
    result = expand_batch(ledger, batch, mint, pad_ids(directory))
    advise(result.advisories)
    if result.problems:
        emit(rejection(result.problems, "ledger"))
        return 1
    event_log(directory).append(result.events)
    document: dict = {
        "session": directory.name,
        "admitted": dict(Counter(event["e"] for event in result.events)),
        "minted": result.minted,
        "counts": counts_of(ledger),
        "open": [
            leaf_id
            for leaf_id, leaf in ledger.leaves.items()
            if isinstance(leaf.state, Open)
        ],
        "yield": yield_table(events + result.events),
    }
    if result.merged:
        document["merged"] = result.merged
    if args.full:
        document["leaves"] = {
            leaf_id: {"question": leaf.question, **leaf_view(leaf.state)}
            for leaf_id, leaf in ledger.leaves.items()
        }
    emit(document)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    directory = STORE.directory(args.session)
    events = read_events(directory)
    ledger = replay(events)
    meta = read_meta(directory)
    mode = meta.get("mode", "full")
    markers = {
        source_id: f"S{index}"
        for index, source_id in enumerate(ledger.source_order, start=1)
    }
    found = violations(ledger)
    demoted = (
        [line for line in found if line.startswith(INFORMAL_DEMOTED)]
        if mode == "informal"
        else []
    )
    blocking = [line for line in found if line not in demoted]
    if blocking:
        signal(f"{len(blocking)} violation(s); details in the JSON violations array")
    signal("Boundary section is yours: render it where the answer flips inside scope")
    document: dict = {
        "session": directory.name,
        "mode": mode,
        "question": meta.get("question"),
        # Markers first: drafting reads this table before anything else.
        "markers": {
            markers[source_id]: {
                "id": source_id,
                "cls": ledger.sources[source_id].cls,
                "title": ledger.sources[source_id].title,
                "url": ledger.sources[source_id].url,
            }
            for source_id in ledger.source_order
        },
        "sections": sections(ledger),
        "scaffold": scaffold(ledger, markers),
        "violations": blocking,
        "advisories": demoted,
        "hedges": hedges(ledger),
        "yield": yield_table(events),
    }
    if args.full:
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
    parser = argparse.ArgumentParser(description=btm_ponder.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="mint a session for one question")
    init.set_defaults(func=cmd_init)
    init.add_argument("ref", help="two or three keywords, or a directory path")
    init.add_argument("--question", required=True)
    init.add_argument("--focus", default=None)
    init.add_argument(
        "--mode",
        choices=MODES,
        default="full",
        help="informal demotes draft blockers to advisories",
    )
    note = commands.add_parser("note")
    note.set_defaults(func=cmd_note)
    note.add_argument("session", help="session identifier; batch JSON on stdin")
    note.add_argument(
        "--file",
        default=None,
        help="read the batch from this file; retries cost one edit",
    )
    note.add_argument("--full", action="store_true", help="add the leaf dump")
    check = commands.add_parser("check")
    check.set_defaults(func=cmd_check)
    check.add_argument("session", help="session identifier")
    check.add_argument("--full", action="store_true", help="add the leaf dump")
    status = commands.add_parser("status")
    status.set_defaults(func=cmd_status)
    status.add_argument("session", help="session identifier")
    schema = commands.add_parser("schema", help="print the note batch shape")
    schema.set_defaults(func=cmd_schema)
    wire_pad(commands, lambda args: STORE.directory(args.session))
    wire_clean(commands, STORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
