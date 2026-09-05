"""Subprocesses, logged. The one place this skill starts a child process."""

from __future__ import annotations

import subprocess

from btm_corekit import (
    UpstreamError,
)
from btm_setup_env.model import (
    DenvError,
)

INSTALL_TIMEOUT = 3600.0  # seconds; an installer past this is stuck on a lock or prompt


def run_logged(
    what: str,
    cmd: list[str],
    env: dict[str, str],
    stdin_text: str | None = None,
    timeout: float = INSTALL_TIMEOUT,
) -> None:
    """Run quietly; on failure surface the tail, which is where build tools
    put the sentence worth reading."""
    try:
        result = subprocess.run(
            cmd,
            env=env,
            input=stdin_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,  # Surface the output tail as DenvError.
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as err:
        raise UpstreamError(f"{what} produced no exit within {timeout:.0f}s") from err
    if result.returncode != 0:
        tail = "\n".join((result.stdout or "").splitlines()[-40:])
        raise DenvError(f"{what} failed (exit {result.returncode}):\n{tail}")
