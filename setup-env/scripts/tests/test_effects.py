"""The exit contract at the download boundary."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, UpstreamError
from btm_setup_env.effects import _status_failure
from btm_setup_env.model import DenvError


class TestStatusFailure:
    def test_this_member_speaks_the_library_contract(self):
        """Every failure used to exit 1, so a dead link and a dead network
        were the same answer."""
        assert issubclass(DenvError, CommandError)

    @pytest.mark.parametrize("status", [500, 502, 429])
    def test_a_server_fault_or_a_rate_limit_is_retryable(self, status):
        assert isinstance(_status_failure(status, "https://x"), UpstreamError)

    @pytest.mark.parametrize("status", [403, 404])
    def test_a_missing_artifact_is_not(self, status):
        assert not isinstance(_status_failure(status, "https://x"), UpstreamError)
