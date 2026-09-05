"""Bytes in: one capped download, its digest, and its unpacking.

A fetch is idempotent by file presence, so a re-run resumes rather than
refetches. A digest mismatch deletes the file, because the presence check
would otherwise trust a corrupt one forever."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sys
import tarfile
import zipfile
from functools import cache
from pathlib import Path, PurePosixPath

import httpx

from btm_corekit import (
    UpstreamError,
    build_client,
    download,
)

ARCHIVE_CAP_BYTES = 4 * 1024 * 1024 * 1024  # an SDK is large; a runaway is larger


def log(message: str) -> None:
    print(f"btm-setup-env: {message}", file=sys.stderr)


@cache
def _client() -> httpx.Client:
    """Reads run unbounded: archives are large, links slow, and every fetch is
    resumable by re-run. Connect, write, and pool waits stay bounded, so a
    dead peer fails instead of hanging."""
    return build_client("setup-env", read_timeout=None)


def fetch(url: str, target: Path) -> None:
    if target.exists():
        return
    download(_client(), url, target, ARCHIVE_CAP_BYTES)


def verify_sha256(path: Path, expected: str) -> None:
    with path.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != expected:
        # The mechanical repair: fetch() trusts an existing file, so a
        # corrupt download would otherwise poison every re-run.
        path.unlink()
        raise UpstreamError(
            f"digest mismatch for {path.name}\n"
            f"  expected {expected}\n  actual   {actual}\n"
            "removed the corrupt download; re-run to fetch it again"
        )


def _stripped(name: str, strip: int) -> tuple[str, ...] | None:
    parts = PurePosixPath(name).parts[strip:]
    if not parts or ".." in parts or parts[0].startswith("/"):
        return None
    return parts


def extract_zip(archive: Path, dest: Path, strip: int) -> None:
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            parts = _stripped(info.filename, strip)
            if parts is None or info.is_dir():
                continue
            target = dest.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = (info.external_attr >> 16) & 0o170777
            if stat.S_ISLNK(mode):
                target.symlink_to(zf.read(info).decode())
                continue
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            if mode & 0o777:
                os.chmod(target, mode & 0o777)


def extract_tar(archive: Path, dest: Path, strip: int) -> None:
    with tarfile.open(archive) as tf:
        members = []
        for member in tf.getmembers():
            parts = _stripped(member.name, strip)
            if parts is None:
                continue
            member.name = str(PurePosixPath(*parts))
            members.append(member)
        try:
            tf.extractall(dest, members=members, filter="tar")
        except TypeError:  # Python <3.11.4 has no filter parameter.
            tf.extractall(dest, members=members)
