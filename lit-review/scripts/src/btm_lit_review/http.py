"""This member's HTTP client: one pooled connection per process, closed when
the one-shot command exits. HTTP/2, SOCKS, and compression come from the
manifest's httpx extras."""

from __future__ import annotations

import httpx

from btm_corekit import client_for
from btm_lit_review.constants import TIMEOUT_SECONDS


def client() -> httpx.Client:
    """The kernel holds the singleton, keyed by skill and timeout, so every
    call site here shares one pool and one identity chain."""
    return client_for("lit-review", read_timeout=TIMEOUT_SECONDS)
