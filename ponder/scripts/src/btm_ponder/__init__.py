"""Scratchpad and verifier for open-question research sessions.

The agent asks, retrieves, and judges; this engine holds the ledger, admits a
round only when every reference resolves, and derives the drafting scaffold
from what the ledger holds. Subcommands print one JSON document to stdout;
`signal:` lines on stderr advise and never block; `error:` exits 1.
"""
