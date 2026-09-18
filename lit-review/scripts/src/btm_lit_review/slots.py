"""Where each subcommand takes its free-form content. Declared once here, so
the command that writes a slot and the command that reads it cannot drift."""

from __future__ import annotations

from btm_corekit import Optional, Required

FRAMING = Required("framing", inline=False)
QUERY = Required("query", inline=False)
RULE = Required("rule", inline=False)
DECISIONS = Required("decisions", inline=False)
DRAFT = Required("draft", inline=False)
KEYS = Optional("keys")


def key_list(raw: str) -> list[str]:
    """The paper keys a `--keys` value names: comma-separated, trimmed, empties
    dropped, so `"a, b"` and `"a,b"` select the same two papers wherever the
    slot is read."""
    return [key.strip() for key in raw.split(",") if key.strip()]
