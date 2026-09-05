"""This member's HTTP client: one pooled connection per process, closed when
the one-shot command exits. HTTP/2, SOCKS, and compression come from the
manifest's httpx extras."""

from __future__ import annotations

from functools import cache

import httpx

from btm_corekit import build_client
from btm_lit_review.constants import TIMEOUT_SECONDS


@cache
def client() -> httpx.Client:
    return build_client("lit-review", read_timeout=TIMEOUT_SECONDS)
