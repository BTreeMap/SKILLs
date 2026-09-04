"""A query answered twice costs one request.

Results are regenerable, so they live in temp space under an owner-named
directory. `clean` removes them and reports the bytes freed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from btm_corekit import dump, parse_with, tree_bytes
from btm_search_web.records import Result, Results


def cache_dir() -> Path:
    return Path(tempfile.gettempdir()) / "btm-search-web"


def _slot(key: str) -> Path:
    return cache_dir() / (hashlib.sha256(key.encode()).hexdigest() + ".json")


def remembered(key: str) -> list[Result] | None:
    """What this exact query returned before, or None."""
    slot = _slot(key)
    if not slot.is_file():
        return None
    try:
        raw = json.loads(slot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        slot.unlink(missing_ok=True)  # a corrupt slot is regenerable
        return None
    return parse_with(Results, raw, str(slot))


def remember(key: str, results: list[Result]) -> None:
    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    slot = _slot(key)
    partial = slot.with_suffix(".partial")
    partial.write_text(
        json.dumps([dump(row) for row in results], ensure_ascii=False),
        encoding="utf-8",
    )
    partial.replace(slot)


def clean() -> dict[str, Any]:
    directory = cache_dir()
    if not directory.is_dir():
        return {"removed": None, "bytes_freed": 0}
    freed = tree_bytes(directory)
    shutil.rmtree(directory)
    return {"removed": str(directory), "bytes_freed": freed}
