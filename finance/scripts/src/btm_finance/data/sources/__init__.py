"""One module per source: a pure parser from bytes to rows, plus a fetch that
reaches the network only through the kernel client."""

from __future__ import annotations

import httpx

from btm_corekit import CommandError, client_for

SKILL = "finance"
TIMEOUT = 60.0


def client() -> httpx.Client:
    return client_for(SKILL, read_timeout=TIMEOUT)


def not_found(err: CommandError) -> bool:
    return err.status == 404  # noqa: PLR2004 - HTTP Not Found
