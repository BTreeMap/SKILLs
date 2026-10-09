"""Every documented command binding isolates the caller's environment."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from btm_repo_gate.conventions import BINDING, BINDING_MARK, MEMBER_DIR
from btm_repo_gate.repairs import Finding
from btm_repo_gate.snapshot import Repo


def rule_binding(repo: Repo) -> Iterator[Finding]:
    """A skill doc line that runs `uv run --project` is the exact binding, or
    quotes the generic form in backticks as the rule's statement; a skill with a
    member documents at least one. Reported, never repaired: the lines around a
    binding (`$R <verb>`) depend on its shape."""
    statement = f"`{BINDING.format(skill='<skill>')}`"
    docs_by_skill: dict[str, list[Path]] = {}
    for path in sorted(repo.texts):
        if path.suffix == ".md" and len(path.parts) > 1:
            docs_by_skill.setdefault(path.parts[0], []).append(path)
    for skill in sorted(repo.skills):
        expected = BINDING.format(skill=skill)
        bound = False
        for path in docs_by_skill.get(skill, []):
            text = repo.texts[path]
            if BINDING_MARK not in text:
                continue
            for number, line in enumerate(text.split("\n"), start=1):
                if BINDING_MARK not in line:
                    continue
                if line == expected:
                    bound = True
                elif statement not in line:
                    yield Finding(
                        "binding",
                        f"{path}:{number}",
                        f"binding must be the line {expected}",
                    )
        manifest = Path(skill) / MEMBER_DIR / "pyproject.toml"
        if manifest in repo.texts and not bound:
            yield Finding(
                "binding",
                skill,
                f"{manifest} has no documented binding; add the line {expected}",
            )
