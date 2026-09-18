"""Regenerable state: one temp-space cache per skill.

Nothing here is authoritative. A slot that will not parse is dropped and
recomputed, and `clean_cache` removes the whole directory, so the worst a
corrupt cache costs is the request that filled it.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Any

from btm_corekit.store.fsio import tree_bytes


def cache_dir(skill: str) -> Path:
    """One owner-named directory in temp space, so `clean` removes what this
    skill wrote and nothing else."""
    return Path(tempfile.gettempdir()) / f"btm-{skill}"


def cache_slot(skill: str, key: str, suffix: str) -> Path:
    """The slot for one natural key: the digest is the file name, so the same
    key always names the same slot and no key can escape the directory."""
    return cache_dir(skill) / (hashlib.sha256(key.encode()).hexdigest() + suffix)


def clean_cache(skill: str) -> dict[str, Any]:
    """Remove the skill's cache and report what it freed, in the keys every
    member's `clean` uses: `{removed, bytes_freed}`."""
    directory = cache_dir(skill)
    if not directory.is_dir():
        return {"removed": None, "bytes_freed": 0}
    freed = tree_bytes(directory)
    shutil.rmtree(directory)
    return {"removed": str(directory), "bytes_freed": freed}
