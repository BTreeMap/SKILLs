#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""Launcher for the btm-ponder workspace member.

uv resolves workspace and path sources lexically, and an agent reaches this
skill through an alias directory such as `.claude/skills/ponder/`, where a
relative path escapes the repository. Resolving this file first turns any
alias path into the member's real location, so no alias-side symlink is
needed. The program itself lives in `../src/btm_ponder/`.
"""

import os
import sys
from pathlib import Path

environment = dict(os.environ)
environment.pop("VIRTUAL_ENV", None)  # an ambient venv is not this member's
member = Path(__file__).resolve().parent.parent
os.execvpe(
    "uv",
    ["uv", "run", "--project", str(member), "btm-ponder", *sys.argv[1:]],
    environment,
)
