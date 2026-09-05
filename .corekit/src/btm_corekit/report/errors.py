"""The one failure type every command boundary understands."""

from __future__ import annotations


class CommandError(Exception):
    """Failure that ends a command with a clean message and exit code 1."""

    status: int | None = None
    """The HTTP status this failure came from, where one did. A caller that
    reads a status its own way (a metered service spelling an exhausted
    budget as a conflict) matches on this rather than on the message."""


class UpstreamError(CommandError):
    """Remote service or network failure; exit code 2, worth retrying."""
