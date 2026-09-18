"""The command surface: one JSON record per verb, and what each refusal
costs the caller."""

from __future__ import annotations

import json

import pytest

from btm_setup_env.cli import _build_plan, _report, main
from btm_setup_env.shell.commands import ProbeResult


def record(capsys) -> dict:
    """Stdout decoded as one document. Two would not parse, which is the
    point: every verb writes exactly one."""
    return json.loads(capsys.readouterr().out)


@pytest.fixture
def provisioned(tmp_path):
    """A root clean will accept: a manifest plus one measurable file."""
    root = tmp_path / "denv"
    root.mkdir()
    (root / "manifest.json").write_text(
        json.dumps({"project": str(tmp_path), "spec": [], "host": "linux-64"}),
        encoding="utf-8",
    )
    (root / "payload").write_bytes(b"x" * 100)
    return root


def clean(root, tmp_path, *flags):
    return main(["clean", "--project", str(tmp_path), "--root", str(root), *flags])


class TestClean:
    def test_a_root_without_a_manifest_survives(self, tmp_path, capsys):
        root = tmp_path / "denv"
        root.mkdir()
        assert clean(root, tmp_path) == 1
        assert "no manifest.json" in capsys.readouterr().err
        assert root.exists()

    def test_removal_reports_the_root_and_the_bytes(
        self, provisioned, tmp_path, capsys
    ):
        assert clean(provisioned, tmp_path) == 0
        document = record(capsys)
        assert document["removed"] == str(provisioned)
        assert document["bytes_freed"] >= 100
        assert not provisioned.exists()

    def test_all_is_refused_because_no_registry_of_roots_exists(
        self, provisioned, tmp_path, capsys
    ):
        assert clean(provisioned, tmp_path, "--all") == 1
        assert "no registry of roots" in capsys.readouterr().err
        assert provisioned.exists()


class TestVerbs:
    def test_a_bare_tag_is_not_a_verb(self, capsys):
        """Nothing is inserted in front of an unknown first token, so the
        rejection names the choice rather than planning something."""
        assert main(["python"]) == 1
        assert "invalid choice" in capsys.readouterr().err

    def test_design_emits_the_plan_and_touches_nothing(self, tmp_path, capsys):
        root = tmp_path / "denv"
        assert (
            main(["design", "python", "--project", str(tmp_path), "--root", str(root)])
            == 0
        )
        document = record(capsys)
        assert document["root"] == str(root)
        assert document["steps"] and document["probes"]
        assert not root.exists()

    def test_list_names_every_target(self, capsys):
        assert main(["list"]) == 0
        targets = record(capsys)["targets"]
        assert {"python", "rust"} <= {row["tag"] for row in targets}
        assert all(row["summary"] for row in targets)

    def test_status_without_a_root_is_a_rejection(self, tmp_path, capsys):
        assert (
            main(
                [
                    "status",
                    "--project",
                    str(tmp_path),
                    "--root",
                    str(tmp_path / "absent"),
                ]
            )
            == 1
        )
        assert "run provision first" in capsys.readouterr().err


class TestReport:
    """A broken toolchain is a finished run, not a malformed request."""

    def plan(self, tmp_path):
        return _build_plan(tmp_path, tmp_path / "denv", ["python"])

    def test_every_probe_passing_is_ok(self, tmp_path, capsys):
        results = [ProbeResult(("python", "--version"), True, "Python 3.12.0")]
        assert _report(self.plan(tmp_path), results) == 0
        document = record(capsys)
        assert document["ok"] is True
        assert "next" not in document

    def test_a_failed_probe_names_the_repair_and_still_exits_zero(
        self, tmp_path, capsys
    ):
        results = [
            ProbeResult(("python", "--version"), True, "Python 3.12.0"),
            ProbeResult(("uv", "--version"), False, "not found on PATH"),
        ]
        assert _report(self.plan(tmp_path), results) == 0
        captured = capsys.readouterr()
        document = json.loads(captured.out)
        assert document["ok"] is False
        assert "re-run provision" in document["next"]
        assert "1 of 2 probes failed" in captured.err
