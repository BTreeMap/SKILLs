"""The gate protocol: one definition, so the contract cannot differ per skill."""

from __future__ import annotations

import json
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from btm_corekit import BATCH, Diagnostic, Parser, add_slot, gated


@dataclass
class Result:
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)
    committed: bool = False


def read(capsys) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out)


def batched(path: Path) -> Namespace:
    """The batch as one file, the spelling a retry edits."""
    parser = Parser()
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    add_slot(run, BATCH, "the batch")
    return parser.parse_args(["run", "--batch:file", str(path)])


class TestGateProtocol:
    def test_a_clean_batch_commits_and_returns_zero(self, capsys, tmp_path):
        path = tmp_path / "b.json"
        path.write_text('{"a": 1}')
        seen = Result()

        def expand(batch: dict[str, Any]) -> Result:
            assert batch == {"a": 1}
            return seen

        code = gated(BATCH, batched(path), "ledger", expand, lambda r: {"ok": True})
        assert code == 0 and read(capsys) == {"ok": True}

    def test_problems_refuse_before_the_commit_runs(self, capsys, tmp_path):
        path = tmp_path / "b.json"
        path.write_text("{}")
        problems = [Diagnostic("a", "fix a"), Diagnostic("b", "fix b")]
        committed = False

        def commit(result: Result) -> dict[str, Any]:
            nonlocal committed
            committed = True
            return {}

        args = batched(path)
        code = gated(BATCH, args, "ledger", lambda _: Result(problems=problems), commit)
        document = read(capsys)
        assert code == 1 and not committed
        assert document["unchanged"] == "ledger"
        assert len(document["rejected"]) == 2

    def test_unparsable_json_is_refused_in_the_same_envelope(self, capsys, tmp_path):
        path = tmp_path / "b.json"
        path.write_text("{not json")

        def expand(batch: dict[str, Any]) -> Result:
            raise AssertionError("expansion must not run on unparsable input")

        code = gated(BATCH, batched(path), "notebook", expand, lambda r: {})
        assert code == 1 and read(capsys)["unchanged"] == "notebook"

    def test_advisories_reach_stderr_even_when_the_batch_is_clean(
        self, capsys, tmp_path
    ):
        path = tmp_path / "b.json"
        path.write_text("{}")
        gated(
            BATCH,
            batched(path),
            "ledger",
            lambda _: Result(advisories=["watch this"]),
            lambda r: {"ok": True},
        )
        assert "watch this" in capsys.readouterr().err
