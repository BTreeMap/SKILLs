"""The parse boundary onto the catalog: one written tag becomes a Target.

A tag is the only untrusted string this skill admits, so this is where an
unknown family is refused with the nearest names rather than admitted and
failed later.
"""

from __future__ import annotations

import difflib

from btm_setup_env.catalog import CATALOG
from btm_setup_env.model import GENERIC, DenvError, RawTag, RecipeKey, Target

_ALIAS = {
    "js": "javascript",
    "node": "javascript",
    "ts": "typescript",
    "py": "python",
    "golang": "go",
    "c++": "cpp",
    "cs": "csharp",
    "dotnet": "csharp",
    "sh": "bash",
    "shell": "bash",
}


def resolve_tag(raw: RawTag) -> Target:
    family = _ALIAS.get(raw.family, raw.family)
    key: RecipeKey = (family, raw.flavor)
    if family == "android" and raw.flavor == GENERIC:
        key = ("java", "android")
    recipe = CATALOG.get(key)
    if recipe is None:
        known = sorted(f if fl == GENERIC else f"{f}:{fl}" for f, fl in CATALOG)
        asked = raw.family if raw.flavor == GENERIC else f"{raw.family}:{raw.flavor}"
        hints = difflib.get_close_matches(asked, known, n=3)
        hint = f"; did you mean {', '.join(hints)}?" if hints else ""
        raise DenvError(
            f"unknown target {asked!r}{hint}\nknown targets: {', '.join(known)}"
        )
    if raw.version is not None and recipe.version_doc is None:
        raise DenvError(f"{family} does not take a version")
    return Target(key, raw.version)
