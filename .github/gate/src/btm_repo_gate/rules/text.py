"""Characters this repository forbids anywhere."""

from __future__ import annotations

from collections.abc import Iterator

from btm_repo_gate.conventions import EM_DASH
from btm_repo_gate.repairs import Finding
from btm_repo_gate.snapshot import Repo


def rule_em_dash(repo: Repo) -> Iterator[Finding]:
    """AGENTS.md forbids U+2014 outright. The replacement is a hyphen, a comma,
    a colon, or a restructured sentence, which is a judgment, so no repair."""
    for path, text in repo.texts.items():
        if EM_DASH not in text:  # Skip per-line scan for most files.
            continue
        for number, line in enumerate(text.split("\n"), start=1):
            if EM_DASH in line:
                yield Finding(
                    "em-dash",
                    f"{path}:{number}",
                    "em-dash (U+2014); use a hyphen, comma, colon, or rewrite",
                )
