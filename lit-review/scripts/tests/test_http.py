"""The OpenAlex credential and the JSON the member expects back."""

from __future__ import annotations

import httpx
import pytest

from btm_corekit import UpstreamError
from btm_lit_review.http import _trial_advisory, http_get_json, openalex_params


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


def test_a_non_json_body_names_its_source(monkeypatch):
    monkeypatch.setattr(
        "btm_lit_review.http._client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b"<html>")
            )
        ),
    )
    with pytest.raises(UpstreamError, match="non-JSON"):
        http_get_json("https://example.org/x")
