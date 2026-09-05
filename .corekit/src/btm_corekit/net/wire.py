"""The tolerance boundary. Everything a foreign service sends enters here.

Inside this layer a record is tolerant on purpose. Outside it nothing is: a
decoder turns one wire record into a domain value whose type says exactly
what is known, and past that point no field is a stand-in for a missing one.

The tolerance has three parts and no more:

  - An unknown key is ignored, so a service may add a field without
    breaking a caller that never asked for it.
  - A null reads as an absent key. A service spells "nothing here" both
    ways and means the same by them.
  - Every field states its own absence in its type, and no field carries a
    stand-in default. A title the service did not send arrives as None,
    never as "", so a crossing cannot mistake silence for an answer.

What that leaves is the third case, which no tolerance covers: a key whose
value is the wrong *kind*. That is the service having changed shape, and it
arrives as a located `UpstreamError` naming the field, because the fix is a
decoder edit rather than anything the caller can retry into.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TypeVar

import httpx
from pydantic import ConfigDict, ValidationError, model_validator

from btm_corekit.net.http import get_bytes
from btm_corekit.records.models import Model, diagnostics
from btm_corekit.report.errors import UpstreamError

W = TypeVar("W", bound="Upstream")


class Upstream(Model):
    """A record another service owns and may extend at any time."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _null_is_absent(cls, raw: Any) -> Any:
        """OpenAlex nulls `primary_location.source` for a work with no venue,
        Wikipedia nulls a page's `description`, Crossref nulls a date part. A
        field's declared absence covers the missing key; this makes the
        explicit null reach it."""
        if not isinstance(raw, Mapping):
            return raw
        return {key: value for key, value in raw.items() if value is not None}


def decode(model: type[W], body: Any, url: str) -> W:
    """One parsed body as the wire record that names its shape."""
    try:
        return model.model_validate(body)
    except ValidationError as err:
        problems = "; ".join(f"{d.where}: {d.fix}" for d in diagnostics(err))
        raise UpstreamError(
            f"{url} no longer answers as {model.__name__} parses it: {problems}"
        ) from err


def json_body(
    model: type[W],
    client: httpx.Client,
    url: str,
    cap: int,
    params: Mapping[str, str] | None = None,
) -> W:
    """One JSON response, capped, decoded into its wire record."""
    payload = get_bytes(client, url, cap, params)
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as err:
        raise UpstreamError(f"non-JSON response from {url}") from err
    return decode(model, body, url)
