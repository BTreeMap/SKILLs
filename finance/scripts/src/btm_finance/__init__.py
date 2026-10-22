"""Kernel of a slow-money research book: layout, ledger, scorecard, sizing,
and the views an agent runs its loop from, in six verbs.

The book is a git repository the agent extends; this package holds what
every book shares. `record` is the ledger's only writer and accepts a batch
only when every reference resolves; `check` derives every verdict from the
ledger and git at read time. Subcommands print one JSON document to stdout;
`signal:` lines on stderr warn and never block; `error:` exits 1.
"""

__version__ = "0.1.0"
