"""HTTP effects over httpx, under the kernel's request identity.

One pooled client per process, closed when the one-shot command exits;
HTTP/2, SOCKS, and compression come from the manifest's httpx extras.
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping
from functools import cache
from typing import Any

import httpx

from btm_corekit import (
    OPENALEX_KEY_ENV,
    CommandError,
    Keyed,
    Trial,
    UpstreamError,
    openalex_access,
    signal,
    user_agent,
)
from btm_lit_review.constants import (
    DOI_HOST,
    HTTP_BAD_REQUEST,
    HTTP_SERVER_ERROR,
    HTTP_TOO_MANY_REQUESTS,
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


def _failure(status: int, url: str) -> CommandError:
    """A 5xx or a rate limit may clear on a retry; any other 4xx is the
    request's own problem, and retrying it changes nothing."""
    text = f"HTTP {status} from {url}"
    if status >= HTTP_SERVER_ERROR or status == HTTP_TOO_MANY_REQUESTS:
        return UpstreamError(text)
    return CommandError(text)


def http_get(url: str, params: Mapping[str, str] | None = None) -> bytes:
    """The body, streamed under a byte cap so a slow drip cannot grow without
    bound inside the per-read timeout."""
    chunks: list[bytes] = []
    size = 0
    try:
        with _client().stream("GET", url, params=params) as response:
            if response.status_code >= HTTP_BAD_REQUEST:
                raise _failure(response.status_code, str(response.url))
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


@cache
def _trial_advisory() -> None:
    """Once per process; the cache is the guard."""
    signal(
        "no OpenAlex key: these calls spend a small daily budget, then 429; "
        f"set {OPENALEX_KEY_ENV} to a free key from openalex.org/settings/api"
    )


def openalex_params() -> dict[str, str]:
    """The key OpenAlex has required since 2026-02-13, or nothing. Pure."""
    match openalex_access():
        case Keyed(key):
            return {"api_key": key}
        case Trial():
            return {}


def openalex_json(url: str, params: Mapping[str, str] | None = None) -> Any:
    """Every OpenAlex call goes through here, so the key is never forgotten."""
    keyed = openalex_params()
    if not keyed:
        _trial_advisory()
    return http_get_json(url, {**(params or {}), **keyed})


def doi_resolution_status(doi: str) -> int:
    """HEAD https://doi.org/<doi> without following the redirect.

    `quote` keeps a `#` or `?` inside a DOI part of the path.
    """
    target = f"https://{DOI_HOST}/{urllib.parse.quote(doi)}"
    try:
        return _client().head(target, follow_redirects=False).status_code
    except httpx.RequestError as err:
        raise UpstreamError(f"cannot reach {DOI_HOST}: {err}") from err
