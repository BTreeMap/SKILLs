#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""Launcher for the btm-repo-gate workspace member.

uv resolves workspace and path sources lexically, so an entry point invoked
through a symlinked path would resolve relative sources outside the
repository. Resolving this file first turns any such path into the member's
real location. The program itself lives in `../src/btm_repo_gate/`.
"""

import os
import sys
from pathlib import Path

environment = dict(os.environ)
environment.pop("VIRTUAL_ENV", None)  # an ambient venv is not this member's
member = Path(__file__).resolve().parent.parent
os.execvpe(
    "uv",
    ["uv", "run", "--project", str(member), "btm-repo-gate", *sys.argv[1:]],
    environment,
)
