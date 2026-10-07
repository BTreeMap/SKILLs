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
    dump,
    emit,
    gated,
    now_iso,
    pad_ids,
    parse_model,
    run_cli,
    wire_clean,
    wire_pad,
)
from btm_draft_paper.batch import SCHEMA, NoteResult, expand_batch
from btm_draft_paper.run import (
    GATE_STAGE,
    STORE,
    TRACE,
    Format,
    InputState,
    RunMeta,
    Verb,
)
from btm_draft_paper.trace import Outcome, RunState, Status, load
from btm_draft_paper.views import check_view, next_step, status_view

OUTCOMES = {
    Outcome.APPROVE: "the gate passes; stages past it open",
    Outcome.REVISE: "the gate stays closed; revise at its stage, then request it again",
    Outcome.REJECT: "the run closes; nothing more is admitted",
}
STATUSES = {
    Status.SUPPORTED: "the artifact backs the claim as written; artifact must "
    "exist, location required",
    Status.EXPLORATORY: "post-hoc analysis the draft labels as such; artifact "
    "must exist, location required",
    Status.UNSUPPORTED: "no artifact backs it; blocks the draft gate",
    Status.TO_RUN: "a planned artifact path; blocks the draft gate",
}


def cmd_init(args: argparse.Namespace) -> int:
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
            "state": args.state,
            "venue": args.venue,
            "model": args.model,
            "artifacts": str(artifacts),
            "created": now_iso(),
        },
        "init",
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


def cmd_note(args: argparse.Namespace) -> int:
    run = load(args.session)

    def expand(batch: dict[str, Any]) -> NoteResult:
        return expand_batch(run.state, batch, pad_ids(run.directory))

    def commit(result: NoteResult) -> dict[str, Any]:
        stamped = [{"run": run.meta.run, **event} for event in result.events]
        EventLog(run.directory / TRACE).append(stamped, held=len(run.rows))
        document: dict[str, Any] = {
            "session": run.directory.name,
            "admitted": dict(Counter(event["event"] for event in result.events)),
            "stage": run.state.stage,
            "gates": dict(run.state.gates),
            "next": next_step(run.state),
        }
        if result.minted:
            document["minted"] = result.minted
        return document

    return gated(BATCH, args, "trace", expand, commit)


def cmd_status(args: argparse.Namespace) -> int:
    emit(status_view(load(args.session)))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    emit(check_view(load(args.session)))
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    emit(
        {
            "note_batch": {"events": list(SCHEMA.values())},
            "order": "events apply in array order; a later event may cite a "
            "claim minted earlier in the batch",
            "gates": {
                gate: f"closes stage {stage}" for gate, stage in GATE_STAGE.items()
            },
            "outcomes": dict(OUTCOMES),
            "statuses": dict(STATUSES),
            "refs": REFS_SCHEMA + "; receipts echo every minted id",
            "pad": PAD_SCHEMA + "; suggested kinds: framing, punch, concern, thread",
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_draft_paper.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="mint a run and pin its intake facts")
    init.set_defaults(func=cmd_init)
    init.add_argument("ref", help="two or three keywords, or a directory path")
    init.add_argument("--verb", type=Verb, choices=list(Verb), required=True)
    init.add_argument("--format", type=Format, choices=list(Format), required=True)
    init.add_argument(
        "--state", type=InputState, choices=list(InputState), required=True
    )
    init.add_argument("--venue", required=True, help="target venue and track")
    init.add_argument("--model", required=True, help="backbone model version")
    init.add_argument(
        "--artifacts",
        default=".",
        help="root that claim artifact paths resolve against",
    )
    note = commands.add_parser("note", help="admit one batch of trace events")
    note.set_defaults(func=cmd_note)
    note.add_argument("session", help="session identifier or directory")
    add_slot(note, BATCH, '{"events": [...]}; schema prints each kind')
    status = commands.add_parser(
        "status", help="stage, gates, claim counts, and the next step"
    )
    status.set_defaults(func=cmd_status)
    status.add_argument("session", help="session identifier or directory")
    check = commands.add_parser(
        "check", help="the gate summary and the evidence ledger"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("session", help="session identifier or directory")
    schema = commands.add_parser("schema", help="print every event shape")
    schema.set_defaults(func=cmd_schema)
    wire_pad(commands, lambda args: STORE.directory(args.session))
    wire_clean(commands, STORE)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
