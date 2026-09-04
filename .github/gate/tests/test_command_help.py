"""Every subcommand names itself, because --help is what an agent reads first."""

from __future__ import annotations

from pathlib import Path

from btm_repo_gate.rules.commands import rule_command_help
from btm_repo_gate.snapshot import Repo


def repo_with(source: str, name: str = "skill/scripts/src/pkg/cli.py") -> Repo:
    return Repo(skills=frozenset(), texts={Path(name): source}, links={}, manifests={})


SILENT = """
def build(sub):
    sub.add_parser("note")
"""

NAMED = """
def build(sub):
    sub.add_parser("note", help="admit one batch")
"""


def test_a_parser_without_help_is_reported():
    [finding] = rule_command_help(repo_with(SILENT))
    assert finding.rule == "command-help"
    assert "'note'" in finding.message
    assert finding.repair is None  # only the author knows what it does


def test_a_parser_with_help_passes():
    assert list(rule_command_help(repo_with(NAMED))) == []


def test_a_test_fixture_is_not_a_command_surface():
    assert list(rule_command_help(repo_with(SILENT, "skill/scripts/tests/t.py"))) == []


def test_a_parser_named_by_a_variable_still_reports_its_line():
    source = (
        "def build(sub):\n    for verb in ('a', 'b'):\n        sub.add_parser(verb)\n"
    )
    [finding] = rule_command_help(repo_with(source))
    assert finding.path.endswith(":3")
