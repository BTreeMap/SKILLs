"""The exit contract at the download boundary."""

from __future__ import annotations

import os
import sys

import pytest

from btm_corekit import CommandError, UpstreamError
from btm_setup_env.model import DenvError
from btm_setup_env.shell.process import run_logged


class TestExitContract:
    def test_this_member_speaks_the_library_contract(self):
        """A dead link and a dead network were once the same answer."""
        assert issubclass(DenvError, CommandError)


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
