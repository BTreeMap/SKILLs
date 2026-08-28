"""HTTP effects: request identity, retrieval, and DOI resolution."""

from __future__ import annotations

import http.client
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from btm_corekit import CommandError
from btm_lit_review.constants import (
    CONTACT_ENV,
    DEFAULT_CONTACT,
    DOI_HOST,
    TIMEOUT_SECONDS,
    USER_AGENT_ENV,
)


@dataclass(frozen=True, slots=True)
class CustomAgent:
    header: str


@dataclass(frozen=True, slots=True)
class Contact:
    address: str


def request_identity() -> CustomAgent | Contact:
    custom = os.environ.get(USER_AGENT_ENV)
    if custom:
        return CustomAgent(custom)
    return Contact(os.environ.get(CONTACT_ENV) or DEFAULT_CONTACT)


def user_agent() -> str:
    match request_identity():
        case CustomAgent(header):
            return header
        case Contact(address):
            return f"btm-skills/1.0 (lit-review; mailto:{address})"


def polite_params() -> dict[str, str]:
    """The `mailto` pool parameter OpenAlex and Crossref honor. Empty under a
    User-Agent override: the override owns identity, so nothing else marks
    the request."""
    match request_identity():
        case CustomAgent():
            return {}
        case Contact(address):
            return {"mailto": address}


def http_get(url: str, params: Mapping[str, str] | None = None) -> bytes:
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    request = urllib.request.Request(full, headers={"User-Agent": user_agent()})
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
        connection.request("HEAD", path, headers={"User-Agent": user_agent()})
        return connection.getresponse().status
    except OSError as err:
        raise CommandError(f"cannot reach {DOI_HOST}: {err}") from err
    finally:
        connection.close()
