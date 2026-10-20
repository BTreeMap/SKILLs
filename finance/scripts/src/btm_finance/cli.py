"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import btm_finance
from btm_corekit import (
    BATCH,
    PAD_SCHEMA,
    REFS_SCHEMA,
    CommandError,
    Optional,
    Parser,
    add_slot,
    count_lines,
    dispatch,
    dump,
    emit,
    gated,
    make_id,
    now_iso,
    run_cli,
    signal,
    text,
    wire_pad,
    write_atomic,
)
from btm_finance.batch import BATCH_KEYS, SCHEMA, Context, RecordResult, expand_batch
from btm_finance.ledger import (
    ENVELOPE,
    Break,
    Kind,
    Numbered,
    audit,
    current,
    dangling,
    rows_of,
)
from btm_finance.models import Status
from btm_finance.scaffold import scaffold
from btm_finance.store import (
    PAD,
    PAD_DIR,
    Book,
    append_chained,
    ledger_files,
    load_limits,
    open_book,
    proposal_dates,
    read_bytes,
    run_files,
    strategies,
)
from btm_finance.views import (
    by_status,
    families,
    next_step,
    open_hypotheses,
    open_proposals,
)

UNIVERSE = Optional("universe", inline=False)
LATER: dict[str, str] = {
    "load": "stage 2",
    "score": "stage 3b",
    "advise": "stage 4",
}
INCIDENT_TAIL = 10


def positive(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a whole number") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"{value} is no asset cap; pass 1 or more")
    return value


def cmd_start(args: argparse.Namespace) -> int:
    emit(scaffold(Path(args.book).expanduser(), args.cap, text(UNIVERSE, args)))
    return 0


def ids_of(path: Path, key: str = "id") -> list[str]:
    return [
        row[key]
        for _, row in rows_of(read_bytes(path))
        if isinstance(row.get(key), str)
    ]


def run_ids(book: Book) -> list[str]:
    return [run_id for path in run_files(book) for run_id in ids_of(path, "run_id")]


def cmd_record(args: argparse.Namespace) -> int:
    book = open_book(args.book)
    limits = load_limits(book)
    kinds = (Kind.HYPOTHESIS, Kind.CRITIQUE, Kind.DECISION, Kind.FILL)
    ids = {kind: ids_of(book.path_of(kind)) for kind in kinds}
    context = Context(
        families=frozenset(limits.families),
        min_holding_days=limits.min_holding_days,
        ids={**ids, Kind.RUN: run_ids(book)},
        strategies=[strategy.name for strategy in strategies(book)],
        proposals=proposal_dates(book),
    )

    def expand(batch: dict[str, Any]) -> RecordResult:
        return expand_batch(context, batch, make_id, now_iso())

    def commit(result: RecordResult) -> dict[str, Any]:
        accepted: dict[str, int] = {}
        for kind, rows in sorted(result.staged.items()):
            append_chained(book.path_of(kind), rows)
            accepted[kind.value] = len(rows)
        document: dict[str, Any] = {"book": book.meta.id, "accepted": accepted}
        if result.preferences is not None:
            write_atomic(
                book.root / "preferences.json",
                json.dumps(dump(result.preferences), indent=2) + "\n",
            )
            document["preferences"] = "rewritten"
        document["new"] = result.new
        document["next"] = "run check for the continue view"
        return document

    return gated(BATCH, args, "book", expand, commit)


def cmd_check(args: argparse.Namespace) -> int:
    if args.target is not None:
        raise CommandError(
            f"check {args.target}: a target arrives in stage 3b (strategy) and "
            "stage 4 (proposal); run bare check today"
        )
    if args.live:
        raise CommandError("check --live arrives in stage 5; run bare check today")
    book = open_book(args.book)
    emit(continue_view(book))
    return 0


def continue_view(book: Book) -> dict[str, Any]:
    """Every ledger file audited and replayed once: O(ledger bytes)."""
    limits = load_limits(book)
    breaks: list[Break] = []
    lines = 0
    rows: dict[str, list[Numbered]] = {}
    for path in ledger_files(book):
        name = book.relative(path)
        data = read_bytes(path)
        breaks += audit(name, data)
        rows[name] = rows_of(data)
        breaks += dangling(name, rows[name])
        lines += len(rows[name])

    def live(kind: Kind) -> list[dict[str, Any]]:
        return current(rows.get(f"ledger/{kind.file}", []))

    runs = [
        row
        for path in run_files(book)
        for row in current(rows.get(book.relative(path), []))
    ]
    hypotheses, decisions = live(Kind.HYPOTHESIS), live(Kind.DECISION)
    listed = strategies(book)
    known = {s.name: s.status for s in listed if s.status is not None}
    unknown = [
        {"strategy": s.name, "status": s.raw} for s in listed if s.status is None
    ]
    for entry in unknown:
        signal(
            f"strategies/{entry['strategy']}/status reads {entry['status']!r}, "
            f"not one of {'|'.join(Status)}"
        )
    if breaks:
        signal(f"{len(breaks)} ledger break(s); details under incidents.ledger")
    today = datetime.now(UTC).date()
    proposals = open_proposals(proposal_dates(book), decisions, today)
    pending = len(open_hypotheses(hypotheses, runs, decisions))
    return {
        "book": book.meta.id,
        "as_of": now_iso(),
        "strategies": {**by_status(known), "unknown": unknown},
        "families": families(limits, hypotheses, runs, decisions),
        "proposals": proposals,
        "incidents": {
            "ledger": [found.view() for found in breaks],
            "logged": live(Kind.INCIDENT)[-INCIDENT_TAIL:],
        },
        "chain": {"files": len(rows), "lines": lines, "breaks": len(breaks)},
        "pad": {"entries": count_lines(book.root / PAD_DIR / "scratch.jsonl")},
        "next": next_step(breaks, hypotheses, pending, proposals),
    }


def cmd_schema(args: argparse.Namespace) -> int:
    del args
    emit(
        {
            "record_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
            "sequence": "hypotheses, critiques, decisions, fills, holdings, "
            "preferences; a decision may name a hypothesis made earlier in the batch",
            "ledger_line": f"{', '.join(ENVELOPE)} (stamped by record), then the "
            "record; prev is the sha256 hex of the previous line's bytes",
            "corrections": '"supersedes": "<id>" on a new line; newest wins',
            "run_line": "run_id, hypothesis_id, family_id, strategy, data_snapshot, "
            "code_hash, config, scorecard, engine, tolerance, held_out, "
            "exclusions (written by score only)",
            "approval": '{"date": "YYYY-MM-DD", "orders": [{"symbol": "...", '
            '"side": "buy|sell", "quantity": 10, "price": 12.5, '
            '"strategy": "<name>", "adv_participation": 0.004}]} '
            "(the operator writes it; bin/send reads it)",
            "refs": REFS_SCHEMA + "; receipts echo every new id under new",
            "pad": PAD_SCHEMA,
        }
    )
    return 0


def later(verb: str) -> int:
    def refuse() -> int:
        raise CommandError(f"{verb} arrives in {LATER[verb]}; not available yet")

    return dispatch(refuse)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_finance.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="make a book at a new path")
    start.set_defaults(func=cmd_start)
    start.add_argument("book", help="directory to make the book in")
    start.add_argument(
        "--cap", type=positive, default=10_000_000, help="asset cap, default 10000000"
    )
    add_slot(start, UNIVERSE, "CSV with a symbol column and an optional sector column")

    schema = commands.add_parser("schema", help="print every record shape")
    schema.set_defaults(func=cmd_schema)

    record = commands.add_parser("record", help="accept one batch through the gate")
    record.set_defaults(func=cmd_record)
    record.add_argument("book", help="book directory")
    add_slot(record, BATCH, ", ".join(BATCH_KEYS))

    check = commands.add_parser("check", help="continue view and ledger chain audit")
    check.set_defaults(func=cmd_check)
    check.add_argument("book", help="book directory")
    check.add_argument("target", nargs="?", help="refused until stage 3b")
    check.add_argument("--live", action="store_true", help="refused until stage 5")

    for verb, stage in LATER.items():
        stub = commands.add_parser(verb, help=f"arrives in {stage}; refused today")
        stub.add_argument("rest", nargs=argparse.REMAINDER)
    wire_pad(commands, PAD)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    given = list(sys.argv[1:] if argv is None else argv)
    if given and given[0] in LATER:
        return later(given[0])
    return run_cli(build_parser(), given)
