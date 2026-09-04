"""The gate protocol: one definition, so the contract cannot differ per skill."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from btm_corekit import Diagnostic, gated


@dataclass
class Result:
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)
    committed: bool = False


def read(capsys) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out)


class TestGateProtocol:
    def test_a_clean_batch_commits_and_returns_zero(self, capsys, tmp_path):
        path = tmp_path / "b.json"
        path.write_text('{"a": 1}')
        seen = Result()

        def expand(batch: dict[str, Any]) -> Result:
            assert batch == {"a": 1}
            return seen

        code = gated(str(path), "ledger", expand, lambda r: {"ok": True})
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

        code = gated(str(path), "ledger", lambda _: Result(problems=problems), commit)
        document = read(capsys)
        assert code == 1 and not committed
        assert document["unchanged"] == "ledger"
        assert len(document["rejected"]) == 2

    def test_unparsable_json_is_refused_in_the_same_envelope(self, capsys, tmp_path):
        path = tmp_path / "b.json"
        path.write_text("{not json")

        def expand(batch: dict[str, Any]) -> Result:
            raise AssertionError("expansion must not run on unparsable input")

        code = gated(str(path), "notebook", expand, lambda r: {})
        assert code == 1 and read(capsys)["unchanged"] == "notebook"

    def test_advisories_reach_stderr_even_when_the_batch_is_clean(
        self, capsys, tmp_path
    ):
        path = tmp_path / "b.json"
        path.write_text("{}")
        gated(
            str(path),
            "ledger",
            lambda _: Result(advisories=["watch this"]),
            lambda r: {"ok": True},
        )
        assert "watch this" in capsys.readouterr().err
