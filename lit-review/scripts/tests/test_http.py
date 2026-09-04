"""The upstream boundary: which failures are worth a retry, and the key."""

from __future__ import annotations

import httpx
import pytest

from btm_corekit import CommandError, UpstreamError
from btm_lit_review.constants import RESPONSE_CAP_BYTES
from btm_lit_review.http import (
    _failure,
    _trial_advisory,
    http_get,
    http_get_json,
    openalex_params,
)


class TestFailureClass:
    @pytest.mark.parametrize("status", [500, 503, 429])
    def test_a_server_fault_or_a_rate_limit_is_retryable(self, status):
        assert isinstance(_failure(status, "https://x"), UpstreamError)

    @pytest.mark.parametrize("status", [400, 403, 404])
    def test_a_request_fault_is_not(self, status):
        """Exit 2 told the agent to retry a URL that can never resolve."""
        failure = _failure(status, "https://x")
        assert isinstance(failure, CommandError)
        assert not isinstance(failure, UpstreamError)


class TestOpenAlexParams:
    def test_a_key_rides_as_api_key(self, monkeypatch):
        monkeypatch.setenv("BTM_OPENALEX_KEY", "k-123")
        assert openalex_params() == {"api_key": "k-123"}

    def test_without_one_the_params_are_empty(self, monkeypatch):
        monkeypatch.delenv("BTM_OPENALEX_KEY", raising=False)
        assert openalex_params() == {}

    def test_the_trial_budget_is_disclosed_once(self, capsys):
        """A silent trial budget 429s mid-session with no explanation."""
        _trial_advisory.cache_clear()
        _trial_advisory()
        _trial_advisory()
        assert capsys.readouterr().err.count("BTM_OPENALEX_KEY") == 1


def served(handler) -> httpx.Client:
    """A client whose transport answers from a function, so the boundary is
    exercised without a network."""
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestStreamedBody:
    def test_a_body_over_the_cap_is_refused_mid_stream(self, monkeypatch):
        """The cap bounds a slow drip that would otherwise grow inside the
        per-read timeout."""
        oversized = b"x" * (RESPONSE_CAP_BYTES + 1)
        monkeypatch.setattr(
            "btm_lit_review.http._client",
            lambda: served(lambda request: httpx.Response(200, content=oversized)),
        )
        with pytest.raises(UpstreamError, match="exceeds"):
            http_get("https://example.org/big")

    def test_a_missing_record_does_not_ask_for_a_retry(self, monkeypatch):
        monkeypatch.setattr(
            "btm_lit_review.http._client",
            lambda: served(lambda request: httpx.Response(404)),
        )
        with pytest.raises(CommandError) as raised:
            http_get("https://example.org/gone")
        assert not isinstance(raised.value, UpstreamError)

    def test_an_unreachable_host_is_retryable(self, monkeypatch):
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route", request=request)

        monkeypatch.setattr("btm_lit_review.http._client", lambda: served(refuse))
        with pytest.raises(UpstreamError, match="cannot reach"):
            http_get("https://example.org/x")

    def test_a_non_json_body_names_the_source(self, monkeypatch):
        monkeypatch.setattr(
            "btm_lit_review.http._client",
            lambda: served(lambda request: httpx.Response(200, content=b"<html>")),
        )
        with pytest.raises(UpstreamError, match="non-JSON"):
            http_get_json("https://example.org/x")
