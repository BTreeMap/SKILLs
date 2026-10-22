"""Book, ledger, and guards for a slow-money research-to-approval pipeline.

The engine holds the book's append-only ledger, accepts a batch only when
every reference resolves, and derives the continue view from live state.
Subcommands print one JSON document to stdout; `signal:` lines on stderr warn
and never block; `error:` exits 1.
"""

__version__ = "0.1.0"
