"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import btm_ponder
from btm_corekit import (
    Ambiguous,
    CommandError,
    Exact,
    NoMatch,
    Recovered,
    band_signal,
    emit,
    is_pathlike,
    jot,
    mint,
    now_iso,
    pad_body,
    recall,
    resolve,
    run_cli,
    signal,
)
from btm_ponder.batch import BATCH_KEYS, SCHEMA, expand_batch
from btm_ponder.ledger import replay
from btm_ponder.state import MODES, Open, require
from btm_ponder.store import (
    STORE,
    append_events,
    ledger_path,
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


def create_session(directory: Path, name: str, args: argparse.Namespace) -> int:
    meta = {
        "question": args.question,
        "focus": args.focus,
        "mode": args.mode or "full",
        "created": now_iso(),
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
    match resolve(ref, STORE.ids()):
        case Exact(sid):
            if args.mode:
                signal("mode is set at creation; --mode ignored on resume")
            emit(orient(STORE.root() / sid))
        case Recovered(sid):
            signal(f"recovered session '{ref}' -> {sid}; use the full identifier")
            emit(orient(STORE.root() / sid))
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
            return create_session(STORE.root() / full, full, args)
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    directory = STORE.dir_of(args.session)
    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    require(bool(raw.strip()), "note reads the JSON batch from stdin or --file")
    try:
        batch = json.loads(raw)
    except json.JSONDecodeError as err:
        emit(
            {
                "rejected": [
                    {"where": "$", "fix": f"make the batch valid JSON: {err}"}
                ],
                "ledger": "unchanged",
            }
        )
        return 1
    require(isinstance(batch, dict), "note takes one JSON object")
    events = read_events(directory)
    ledger = replay(events)
    result = expand_batch(ledger, batch, mint)
    for line in result.advisories:
        signal(line)
    if result.problems:
        emit(
            {
                "rejected": [problem.view() for problem in result.problems],
                "ledger": "unchanged",
                "next": "apply every fix above to the batch, then resend; "
                "--file makes the retry one edit",
            }
        )
        return 1
    append_events(directory, result.events)
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
    directory = STORE.dir_of(args.session)
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
    directory = STORE.dir_of(args.session)
    events = read_events(directory)
    ledger = replay(events)
    attached = Counter(source.leaf for source in ledger.sources.values())
    emit(
        {
            "session": directory.name,
            "mode": read_meta(directory).get("mode", "full"),
            "counts": counts_of(ledger),
            "sources": len(ledger.sources),
            "swept": ledger.swept,
            "open": [
                {"id": leaf_id, "q": leaf.question, "sources": attached[leaf_id]}
                for leaf_id, leaf in ledger.leaves.items()
                if isinstance(leaf.state, Open)
            ],
            "last_checkpoint": next(
                (
                    event.get("label")
                    for event in reversed(events)
                    if event.get("e") == "checkpoint"
                ),
                None,
            ),
        }
    )
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    emit(
        {
            "note_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
            "order": "leaves, sources, closes, sweeps, checkpoints; later entries "
            "may reference ids minted earlier in the same batch",
            "refs": "a ref is the kw slug, an explicit ref, or any unique keyword "
            "subset; receipts echo every minted id",
            "pad": "jot stores any JSON object unchecked; recall filters by "
            '--kind/--match/--since/--limit; suggested body: {"kind": '
            '"quote|hunch|open", ...}',
        }
    )
    return 0


def session_dir(ref: str) -> Path:
    directory = STORE.dir_of(ref)
    require(
        ledger_path(directory).exists(),
        f"no session at {directory}; open with --question creates one",
    )
    return directory


def cmd_jot(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    body, advisory = pad_body(args.entry, args.text)
    if advisory:
        signal(advisory)
    emit(jot(directory, body))
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    emit(
        recall(
            directory,
            kind=args.kind,
            match=args.match,
            since=args.since,
            limit=args.limit,
        )
    )
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    emit(STORE.clean(args.session, args.all))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=btm_ponder.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    opener = commands.add_parser("open")
    opener.set_defaults(func=cmd_open)
    opener.add_argument("ref", help="two or three keywords in one quoted argument")
    opener.add_argument("--question")
    opener.add_argument("--focus", default=None)
    opener.add_argument(
        "--mode",
        choices=MODES,
        default=None,
        help="informal demotes draft blockers to advisories (set at creation)",
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
    jotter = commands.add_parser("jot", help="free note on the session pad")
    jotter.set_defaults(func=cmd_jot)
    jotter.add_argument("session")
    jotter.add_argument("entry", help="a JSON object, or prose with --text")
    jotter.add_argument("--text", action="store_true", help="store the entry as prose")
    recaller = commands.add_parser("recall", help="filtered slice of the pad")
    recaller.set_defaults(func=cmd_recall)
    recaller.add_argument("session")
    recaller.add_argument("--kind")
    recaller.add_argument("--match")
    recaller.add_argument("--since", help="entries after this pad id")
    recaller.add_argument("--limit", type=int)
    clean = commands.add_parser("clean")
    clean.set_defaults(func=cmd_clean)
    clean.add_argument("session", nargs="?")
    clean.add_argument("--all", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
