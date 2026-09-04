"""The upstream boundary: which failures are worth a retry, and the key."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, UpstreamError
from btm_lit_review.http import _failure, _trial_advisory, openalex_params


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
