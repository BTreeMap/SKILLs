"""A skill's Python is one workspace member rooted at `<skill>/scripts/`."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from btm_repo_gate.conventions import MEMBER_DIR
from btm_repo_gate.repairs import Finding
from btm_repo_gate.snapshot import Repo


def rule_member_layout(repo: Repo) -> Iterator[Finding]:
    """The member holds manifest, `src/`, and `tests/`, so the skill directory
    stays documentation. Moving code is a judgment about imports and history,
    so every finding here is reported, never repaired."""
    # One pass buckets Python files by skill; the loop below reads only its bucket.
    python_by_skill: dict[str, list[Path]] = {}
    for path in sorted(repo.texts):
        if path.suffix == ".py" and path.parts:
            python_by_skill.setdefault(path.parts[0], []).append(path)
    for skill in sorted(repo.skills):
        root = Path(skill)
        member = root / MEMBER_DIR
        manifest = member / "pyproject.toml"
        member_has_code = False
        for path in python_by_skill.get(skill, []):
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
