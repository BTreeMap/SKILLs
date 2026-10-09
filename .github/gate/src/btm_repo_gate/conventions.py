"""The constants AGENTS.md fixes: paths, suffixes, field order, limits."""

from __future__ import annotations

from pathlib import Path

# Escape required because this file is scanned for the forbidden character.
EM_DASH = "\u2014"
TEXT_SUFFIXES = frozenset({".md", ".py", ".toml", ".yml", ".yaml"})
# Tool-managed trees are outside these conventions, so the walk stops there.
PRUNED_DIRS = frozenset(
    {".git", "__pycache__", ".ruff_cache", ".venv", ".pytest_cache", ".mypy_cache"}
)
SPEC_FIELDS = (
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
)
DESCRIPTION_LIMIT = 1024
# Codex gives the whole skill list 8,000 characters when the context window is
# unknown and shortens descriptions first.
DESCRIPTION_BUDGET = 7000
# Markdown prose is wrapped here; code, tables, and markup keep their width.
WRAP_WIDTH = 76
# A skill's Python is one workspace member rooted here; the skill dir stays docs.
MEMBER_DIR = Path("scripts")
# The one brand string this repo publishes: marketplace, plugin, XDG state root.
BRAND = "btm-skills"
# `skills/` is the vendor-neutral hub; vendor paths symlink to it, not the skill.
HUB = Path("skills")
VENDOR_LINKS = (Path(".agents/skills"), Path(".claude/skills"), Path(".github/skills"))
# The one spelling of a skill's command binding (author-skill `scripts`); both
# unsets keep the caller's environment from redirecting uv.
BINDING = (
    'R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project'
    ' $(realpath <skill-root>/scripts) btm-{skill}"'
)
BINDING_MARK = "uv run --project"
# The shared kernel package; a consumer member declares it as a workspace dependency.
KERNEL = Path(".corekit")
MARKETPLACE = Path(".claude-plugin/marketplace.json")
PLUGIN_MANIFEST = Path(".claude-plugin/plugin.json")


def split_frontmatter(text: str) -> tuple[str, int] | None:
    """(YAML body, offset of the first line after the closing `---`) when the
    text opens with a `---` line and a later line is exactly `---`; one pass."""
    if not text.startswith("---\n"):
        return None
    position = 4
    while (line_end := text.find("\n", position)) != -1:
        if text[position:line_end] == "---":
            return text[4:position].removesuffix("\n"), line_end + 1
        position = line_end + 1
    return None


# Bound repairs in case future rules unlock one another.
FIXPOINT_ROUNDS = 4
