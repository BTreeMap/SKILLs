"""Argument surface: the gate, the derived views, the pad, and clean."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import btm_draft_paper
from btm_corekit import (
    BATCH,
    PAD_SCHEMA,
    REFS_SCHEMA,
    CommandError,
    EventLog,
    Parser,
    add_slot,
    corpus_connection,
    corpus_path,
    dump,
    emit,
    gated,
    now_iso,
    pad_ids,
    parse_model,
    read_shelf,
    run_cli,
    wire_cite,
    wire_clean,
    wire_pad,
    wire_project,
)
from btm_draft_paper.batch import SCHEMA, RecordResult, expand_batch
from btm_draft_paper.run import (
    GATE_STAGE,
    STORE,
    TRACE,
    Format,
    InputStatus,
    RunMeta,
    Verb,
)
from btm_draft_paper.trace import Outcome, RunState, Status, load
from btm_draft_paper.views import check_view, next_step, status_view

OUTCOMES = {
    Outcome.ACCEPT: "the gate passes; stages past it open",
    Outcome.CHANGE: "the gate stays closed; change at its stage, then request it again",
    Outcome.REJECT: "the run closes; nothing more is accepted",
}
STATUSES = {
    Status.SUPPORTED: "the artifact backs the claim as written; artifact must "
    "exist, location required",
    Status.EXPLORATORY: "post-hoc analysis the draft labels as such; artifact "
    "must exist, location required",
    Status.UNSUPPORTED: "no artifact backs it; blocks the draft gate",
    Status.TO_RUN: "a planned artifact path; blocks the draft gate",
}


def cmd_start(args: argparse.Namespace) -> int:
    made = STORE.create(args.ref)
    artifacts = Path(args.artifacts).expanduser().resolve()
    if not artifacts.is_dir():
        raise CommandError(f"--artifacts {artifacts} is not a directory")
    meta = parse_model(
        RunMeta,
        {
            "run": made.directory.name,
            "verb": args.verb,
            "format": args.format,
            "status": args.status,
            "venue": args.venue,
            "model": args.model,
            "artifacts": str(artifacts),
            "created": now_iso(),
            "project": args.project,
        },
        "start",
    )
    STORE.write_meta(made.directory, meta)
    EventLog(made.directory / TRACE).touch()
    state = RunState.of(meta)
    emit(
        {
            "session": made.name,
            "dir": str(made.directory),
            **dump(meta),
            "stages": list(meta.stages()),
            "gates": {gate: GATE_STAGE[gate] for gate in state.gates},
            "next": next_step(state),
        }
    )
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    run = load(args.session)

    def expand(batch: dict[str, Any]) -> RecordResult:
        return expand_batch(run.state, batch, pad_ids(run.directory))

    def commit(result: RecordResult) -> dict[str, Any]:
        stamped = [{"run": run.meta.run, **event} for event in result.events]
        EventLog(run.directory / TRACE).append(stamped, held=len(run.rows))
        document: dict[str, Any] = {
            "session": run.directory.name,
            "accepted": dict(Counter(event["event"] for event in result.events)),
            "stage": run.state.stage,
            "gates": dict(run.state.gates),
            "next": next_step(run.state),
        }
        if result.new:
            document["new"] = result.new
        return document

    return gated(BATCH, args, "trace", expand, commit)


def cmd_attach(args: argparse.Namespace) -> int:
    run = load(args.session)
    path = corpus_path(args.corpus)
    shelf = read_shelf(path)
    meta = run.meta.with_(corpus=str(path)).with_connection(corpus_connection(path))
    STORE.write_meta(run.directory, meta)
    emit(
        {
            "session": run.directory.name,
            "corpus": str(path),
            "records": len(shelf.works),
            "as_of": shelf.as_of,
            "next": "record citation-added per citation; check resolves each ref",
        }
    )
    return 0


def attached_corpus(session: str) -> Path | None:
    corpus = STORE.read_meta(STORE.directory(session), RunMeta).corpus
    return Path(corpus) if corpus else None


def cmd_status(args: argparse.Namespace) -> int:
    emit(status_view(load(args.session)))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    emit(check_view(load(args.session)))
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    emit(
        {
            "record_batch": {"events": list(SCHEMA.values())},
            "sequence": "events apply in array order; a later event may cite a "
            "claim made earlier in the batch",
            "gates": {
                gate: f"closes stage {stage}" for gate, stage in GATE_STAGE.items()
            },
            "outcomes": dict(OUTCOMES),
            "statuses": dict(STATUSES),
            "refs": REFS_SCHEMA + "; receipts echo every new id",
            "pad": PAD_SCHEMA,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_draft_paper.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="make a run and pin its intake facts")
    start.set_defaults(func=cmd_start)
    start.add_argument("ref", help="two or three keywords, or a directory path")
    start.add_argument("--verb", type=Verb, choices=list(Verb), required=True)
    start.add_argument("--format", type=Format, choices=list(Format), required=True)
    start.add_argument(
        "--status", type=InputStatus, choices=list(InputStatus), required=True
    )
    start.add_argument("--venue", required=True, help="target venue and track")
    start.add_argument("--model", required=True, help="backbone model version")
    start.add_argument(
        "--artifacts",
        default=".",
        help="root that claim artifact paths resolve against",
    )
    wire_project(start)
    record = commands.add_parser("record", help="accept one batch of trace events")
    record.set_defaults(func=cmd_record)
    record.add_argument("session", help="session identifier or directory")
    add_slot(record, BATCH, '{"events": [...]}; schema prints each kind')
    status = commands.add_parser(
        "status", help="stage, gates, claim counts, and the next step"
    )
    status.set_defaults(func=cmd_status)
    status.add_argument("session", help="session identifier or directory")
    attach = commands.add_parser(
        "attach", help="attach a lit-review corpus; its records need no re-retrieval"
    )
    attach.set_defaults(func=cmd_attach)
    attach.add_argument("session", help="session identifier or directory")
    attach.add_argument("--corpus", required=True, help="lit-review session id or path")
    check = commands.add_parser(
        "check", help="the gate summary, the evidence ledger, and the citations"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("session", help="session identifier or directory")
    schema = commands.add_parser("schema", help="print every event shape")
    schema.set_defaults(func=cmd_schema)
    wire_pad(commands, STORE)
    wire_cite(commands, STORE.skill, attached_corpus)
    wire_clean(commands, STORE)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
