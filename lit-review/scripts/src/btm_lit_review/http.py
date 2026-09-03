"""HTTP effects over httpx, under the kernel's request identity.

One pooled client per process; HTTP/2, SOCKS proxies, and brotli/zstd
encodings come from the manifest's httpx extras and negotiate themselves.
Commands are one-shot, so process exit closes the pool.
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping
from functools import cache
from typing import Any

import httpx

from btm_corekit import UpstreamError, user_agent
from btm_lit_review.constants import (
    DOI_HOST,
    HTTP_BAD_REQUEST,
    RESPONSE_CAP_BYTES,
    TIMEOUT_SECONDS,
)


@cache
def _client() -> httpx.Client:
    return httpx.Client(
        http2=True,
        follow_redirects=True,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": user_agent("lit-review")},
    )


def http_get(url: str, params: Mapping[str, str] | None = None) -> bytes:
    """The body, streamed under a byte cap so a slow drip cannot grow without
    bound inside the per-read timeout."""
    chunks: list[bytes] = []
    size = 0
    try:
        with _client().stream("GET", url, params=params) as response:
            if response.status_code >= HTTP_BAD_REQUEST:
                raise UpstreamError(f"HTTP {response.status_code} from {response.url}")
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > RESPONSE_CAP_BYTES:
                    raise UpstreamError(
                        f"response from {response.url} exceeds "
                        f"{RESPONSE_CAP_BYTES} bytes"
                    )
                chunks.append(chunk)
    except httpx.RequestError as err:
        raise UpstreamError(f"cannot reach {err.request.url}: {err}") from err
    return b"".join(chunks)


def http_get_json(url: str, params: Mapping[str, str] | None = None) -> Any:
    payload = http_get(url, params)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as err:
        raise UpstreamError(f"non-JSON response from {url}") from err


def doi_resolution_status(doi: str) -> int:
    """HEAD https://doi.org/<doi> without following the redirect.

    `quote` keeps a `#` or `?` inside a DOI part of the path.
    """
    target = f"https://{DOI_HOST}/{urllib.parse.quote(doi)}"
    try:
        return _client().head(target, follow_redirects=False).status_code
    except httpx.RequestError as err:
        raise UpstreamError(f"cannot reach {DOI_HOST}: {err}") from err
