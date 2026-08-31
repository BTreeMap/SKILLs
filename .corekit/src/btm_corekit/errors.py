"""The one failure type every command boundary understands."""

from __future__ import annotations


class CommandError(Exception):
    """Failure that ends a command with a clean message and exit code 1."""


class UpstreamError(CommandError):
    """Remote service or network failure; exit code 2, worth retrying."""
