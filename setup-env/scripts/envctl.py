#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["certifi"]
# ///
"""envctl: provision an isolated, userspace, per-project dev environment.

Entry point only. The whole program lives in the envkit package beside this
file; uv puts this script's directory on sys.path, so the import below is the
single piece of wiring. certifi is the one dependency: it supplies TLS roots
on hosts that ship none (a bare ubuntu:24.04 image), and uv can always fetch
it because uv bundles its own roots.
"""

from envkit.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
