"""The exit contract at the download boundary."""

from __future__ import annotations

import os
import sys

import pytest

from btm_corekit import CommandError, UpstreamError
from btm_setup_env.effects import _status_failure, run_logged
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


class TestRunLogged:
    def test_a_failure_surfaces_the_output_tail(self):
        """Build tools put the sentence worth reading at the end."""
        with pytest.raises(DenvError, match="the last line"):
            run_logged(
                "probe",
                [sys.executable, "-c", "print('the last line'); raise SystemExit(1)"],
                dict(os.environ),
            )

    def test_a_stuck_command_is_retryable(self):
        with pytest.raises(UpstreamError, match="produced no exit"):
            run_logged(
                "probe",
                [sys.executable, "-c", "import time; time.sleep(30)"],
                dict(os.environ),
                timeout=0.5,
            )
