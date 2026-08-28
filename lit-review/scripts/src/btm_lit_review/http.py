"""HTTP effects: retrieval and DOI resolution under the kernel's request identity."""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

from btm_corekit import CommandError, user_agent
from btm_lit_review.constants import (
    DOI_HOST,
    TIMEOUT_SECONDS,
)


def http_get(url: str, params: Mapping[str, str] | None = None) -> bytes:
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    request = urllib.request.Request(
        full, headers={"User-Agent": user_agent("lit-review")}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        raise CommandError(f"HTTP {err.code} from {full}") from err
    except (urllib.error.URLError, TimeoutError) as err:
        raise CommandError(f"cannot reach {full}: {err}") from err


def http_get_json(url: str, params: Mapping[str, str] | None = None) -> Any:
    payload = http_get(url, params)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as err:
        raise CommandError(f"non-JSON response from {url}") from err


def doi_resolution_status(doi: str) -> int:
    """HEAD https://doi.org/<doi> without following the redirect."""
    connection = http.client.HTTPSConnection(DOI_HOST, timeout=TIMEOUT_SECONDS)
    try:
        path = "/" + urllib.parse.quote(doi)
        connection.request(
            "HEAD", path, headers={"User-Agent": user_agent("lit-review")}
        )
        return connection.getresponse().status
    except OSError as err:
        raise CommandError(f"cannot reach {DOI_HOST}: {err}") from err
    finally:
        connection.close()
