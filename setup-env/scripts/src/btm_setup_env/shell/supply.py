"""The two suppliers every recipe is built from: micromamba and uv.

Both are ensured rather than installed: each checks its postcondition
first, so a re-run costs a stat rather than a download."""

from __future__ import annotations

import shutil

from btm_corekit import (
    CommandError,
)
from btm_setup_env.model import (
    DenvError,
)
from btm_setup_env.shell.root import Ctx
from btm_setup_env.shell.transfer import fetch, log, verify_sha256

MICROMAMBA_VERSION = "2.9.0-0"


MICROMAMBA_RELEASES = (
    "https://github.com/mamba-org/micromamba-releases/releases/download"
)


def ensure_micromamba(ctx: Ctx) -> None:
    if ctx.mamba.exists():
        return
    platform = ctx.host.conda_platform.value
    log(f"installing micromamba {MICROMAMBA_VERSION} ({platform})")
    url = f"{MICROMAMBA_RELEASES}/{MICROMAMBA_VERSION}/micromamba-{platform}"
    archive = ctx.layout.downloads / f"micromamba-{platform}"
    fetch(url, archive)
    # Fetch the publisher digest to keep verification architecture-independent.
    sidecar = archive.with_name(archive.name + ".sha256")
    fetch(url + ".sha256", sidecar)
    try:
        verify_sha256(archive, sidecar.read_text().split()[0])
    except CommandError:
        # The sidecar itself may be the corrupt cached file; clear it too so
        # the re-run re-fetches both instead of wedging on a bad pin.
        sidecar.unlink(missing_ok=True)
        raise
    ctx.mamba.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, ctx.mamba)
    ctx.mamba.chmod(0o755)


def uv_binary(ctx: Ctx) -> str:
    """Where uv is. The one supplier this skill does not install: it is the
    bootstrap every member already runs under."""
    found = shutil.which("uv")
    if found is None:
        raise DenvError(
            "uv is required and was not found on PATH; see https://docs.astral.sh/uv/"
        )
    return found
