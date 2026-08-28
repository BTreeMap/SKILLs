"""A skill's Python is one workspace member rooted at `<skill>/scripts/`."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from btm_repo_gate.conventions import MEMBER_DIR
from btm_repo_gate.repairs import Finding
from btm_repo_gate.snapshot import Repo


def rule_member_layout(repo: Repo) -> Iterator[Finding]:
    """The member holds manifest, `src/`, and `tests/`, so the skill directory
    itself stays documentation. Moving code or a manifest is a judgment about
    imports and history, so every finding here is reported, never repaired."""
    for skill in sorted(repo.skills):
        root = Path(skill)
        member = root / MEMBER_DIR
        manifest = member / "pyproject.toml"
        member_has_code = False
        for path in sorted(repo.texts):
            if path.suffix != ".py" or root not in path.parents:
                continue
            if member in path.parents:
                member_has_code = True
            else:
                yield Finding(
                    "member-layout",
                    str(path),
                    f"skill Python belongs under {member}/",
                )
        if member_has_code and manifest not in repo.texts:
            yield Finding(
                "member-layout",
                str(member),
                f"bundled Python needs a member manifest at {manifest}",
            )
        if root / "pyproject.toml" in repo.texts:
            yield Finding(
                "member-layout",
                str(root / "pyproject.toml"),
                f"member manifest belongs at {manifest}",
            )
