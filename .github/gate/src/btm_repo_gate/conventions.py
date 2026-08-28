"""The constants AGENTS.md fixes: paths, suffixes, field order, limits."""

from __future__ import annotations

import re
from pathlib import Path

# Escape required because this file is scanned for the forbidden character.
EM_DASH = "\u2014"
TEXT_SUFFIXES = frozenset({".md", ".py", ".toml", ".yml", ".yaml"})
# Tool-managed trees hold third-party text this repository's conventions do not
# govern, so the walk stops at each one rather than judging its contents.
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
SKILL_SHEBANG = "#!/usr/bin/env -S uv run --script"
PEP_723_OPEN = "# /// script"
# The one abbreviation this repository publishes under: the marketplace name,
# the plugin name, and (by convention documented in AGENTS.md) the XDG state
# root that bundled scripts write beneath.
BRAND = "btm-skills"
# `skills/` is the vendor-neutral hub: one relative symlink per skill, pointing
# back at the canonical root directory. Each vendor path is a single symlink to
# that hub, so supporting another agent costs one link rather than one per
# skill. Installers resolve skills through the manifests instead, which declare
# the canonical paths.
HUB = Path("skills")
VENDOR_LINKS = (Path(".claude/skills"), Path(".github/skills"))
# The shared kernel package consumer scripts declare as a uv path dependency
# (`../.corekit`, resolved lexically). Each consumer skill carries a dotted
# `.corekit` symlink to the repository kernel, so the dependency lands on the
# same package through the canonical path, the hub, and every vendor path.
KERNEL = Path(".corekit")
MARKETPLACE = Path(".claude-plugin/marketplace.json")
PLUGIN_MANIFEST = Path(".claude-plugin/plugin.json")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Bound repairs in case future rules unlock one another.
FIXPOINT_ROUNDS = 4
