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

from btm_corekit import UpstreamError, build_client, get_bytes, openalex_query
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


def openalex_json(url: str, params: Mapping[str, str] | None = None) -> Any:
    """Every OpenAlex call goes through here, so the key is never forgotten."""
    return http_get_json(url, openalex_query(params))


def doi_resolution_status(doi: str) -> int:
    """HEAD https://doi.org/<doi> without following the redirect. `quote`
    keeps a `#` or `?` inside a DOI part of the path."""
    target = f"https://{DOI_HOST}/{urllib.parse.quote(doi)}"
    try:
        return _client().head(target, follow_redirects=False).status_code
    except httpx.HTTPError as err:
        raise UpstreamError(f"cannot reach {DOI_HOST}: {err}") from err
