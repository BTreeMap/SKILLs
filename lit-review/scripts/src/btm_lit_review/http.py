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
    Keyed,
    Trial,
    UpstreamError,
    build_client,
    get_bytes,
    openalex_access,
    signal,
)
from btm_lit_review.constants import DOI_HOST, RESPONSE_CAP_BYTES, TIMEOUT_SECONDS


@cache
def _client() -> httpx.Client:
    return build_client("lit-review", read_timeout=TIMEOUT_SECONDS)


def http_get(url: str, params: Mapping[str, str] | None = None) -> bytes:
    return get_bytes(_client(), url, RESPONSE_CAP_BYTES, params)


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
    """HEAD https://doi.org/<doi> without following the redirect. `quote`
    keeps a `#` or `?` inside a DOI part of the path."""
    target = f"https://{DOI_HOST}/{urllib.parse.quote(doi)}"
    try:
        return _client().head(target, follow_redirects=False).status_code
    except httpx.HTTPError as err:
        raise UpstreamError(f"cannot reach {DOI_HOST}: {err}") from err
