"""The rule set: one function per convention, each pure over the snapshot.

Adding a rule means adding it here, so the registry is the only list to keep.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from btm_repo_gate.repairs import Finding
from btm_repo_gate.rules.commands import rule_command_help
from btm_repo_gate.rules.frontmatter import rule_frontmatter, rule_skill_layout
from btm_repo_gate.rules.generated import rule_listings, rule_manifest
from btm_repo_gate.rules.kernel import rule_kernel
from btm_repo_gate.rules.links import rule_alias
from btm_repo_gate.rules.members import rule_member_layout
from btm_repo_gate.rules.text import rule_em_dash
from btm_repo_gate.snapshot import Repo

RULES: tuple[Callable[[Repo], Iterator[Finding]], ...] = (
    rule_alias,
    rule_command_help,
    rule_em_dash,
    rule_frontmatter,
    rule_kernel,
    rule_listings,
    rule_manifest,
    rule_member_layout,
    rule_skill_layout,
)


def audit(repo: Repo) -> list[Finding]:
    return [finding for rule in RULES for finding in rule(repo)]
