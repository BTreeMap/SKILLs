"""Run trace and gate keeper for paper-drafting runs.

The agent drafts and judges; this engine holds the run's pinned facts and
its append-only trace, accepts a batch of events only when every one is
legal, and derives the current stage, gate standings, evidence ledger, and
next step from the trace on every call. Subcommands print one JSON document
to stdout; `signal:` lines on stderr advise and never block; `error:` exits 1.
"""
