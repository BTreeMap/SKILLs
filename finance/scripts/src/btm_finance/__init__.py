"""Book, ledger, and guards for a slow-money research-to-approval pipeline.

The agent researches and records; this engine holds the book's chained
ledger, accepts a batch only when every reference resolves, and derives the
continue view from live state. Subcommands print one JSON document to stdout;
`signal:` lines on stderr advise and never block; `error:` exits 1.
"""

__version__ = "0.1.0"
