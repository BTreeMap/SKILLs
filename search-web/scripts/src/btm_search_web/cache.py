"""A query answered twice costs one request.

Results are regenerable, so they live in the skill's temp-space cache and no
slot is authoritative: one that will not parse is dropped with a signal and
recomputed, costing the request that filled it. `clean` removes the whole
directory and reports the bytes freed.
"""

from __future__ import annotations

import json
from typing import Any

from btm_corekit import (
    CommandError,
    cache_slot,
    clean_cache,
    dump,
    parse_with,
    signal,
    write_atomic,
)
from btm_search_web.records import Result, Results


def remembered(key: str) -> list[Result] | None:
    """What this exact query returned before, or None. The query string is the
    natural key.

    A slot that will not decode is removed rather than refused: the upstream
    that filled it can fill it again.
    """
    slot = cache_slot("search-web", key, ".json")
    if not slot.is_file():
        return None
    try:
        raw = json.loads(slot.read_text(encoding="utf-8"))
        return parse_with(Results, raw, str(slot))
    except (OSError, json.JSONDecodeError, CommandError):
        slot.unlink(missing_ok=True)
        signal(f"unreadable cache slot dropped, recomputing: {slot}")
        return None


def remember(key: str, results: list[Result]) -> None:
    """Write the rows atomically, so a reader finds a whole slot or none."""
    slot = cache_slot("search-web", key, ".json")
    slot.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(slot, json.dumps([dump(row) for row in results], ensure_ascii=False))


def clean() -> dict[str, Any]:
    return clean_cache("search-web")
