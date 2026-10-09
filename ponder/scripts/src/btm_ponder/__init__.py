"""Scratchpad and verifier for open-question research sessions.

The agent asks, retrieves, and judges; this engine holds the ledger, accepts a
cycle only when every reference resolves, and derives the drafting structure
from what the ledger holds. Subcommands print one JSON document to stdout;
`signal:` lines on stderr advise and never block; `error:` exits 1.
"""
