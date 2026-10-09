"""Argument surface: `render`, one JSON document out."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence

import btm_fact_check
from btm_corekit import (
    Admission,
    CommandError,
    Parser,
    Required,
    add_slot,
    emit,
    rejection,
    run_cli,
    text,
)
from btm_fact_check.render import readiness, report
from btm_fact_check.state import State, Verdict

STATE = Required("state", inline=False)
UNCHANGED = "nothing: render writes no state"


def cmd_render(args: argparse.Namespace) -> int:
    try:
        raw = json.loads(text(STATE, args))
    except json.JSONDecodeError as err:
        raise CommandError(f"make the state valid JSON: {err}") from err
    gate = Admission()
    state = gate.decode(State, raw)
    if state is None:
        emit(rejection(gate.problems, UNCHANGED, STATE))
        return 1
    match readiness(state):
        case Admission(problems=problems):
            emit(rejection(problems, UNCHANGED, STATE))
            return 1
        case ready:
            counts = Counter(item.verdict for item in ready)
            emit(
                {
                    "claims": len(ready),
                    "verdicts": {verdict.value: counts[verdict] for verdict in Verdict},
                    "report": report(state, ready),
                }
            )
            return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_fact_check.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser(
        "render", help="the evidence-first report, derived from the state file"
    )
    render.set_defaults(func=cmd_render)
    add_slot(render, STATE, "the factcheck-state.json object")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
