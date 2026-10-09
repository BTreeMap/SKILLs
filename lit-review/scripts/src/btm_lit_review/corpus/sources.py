"""One fetcher over every index, returning Papers and the reported total,
None where the index reports none.

Every index crosses into the kernel's `Work` first, so the projection into
a Paper is written once rather than once per source.
"""

from __future__ import annotations

from btm_corekit import INDEXES, Window, search
from btm_lit_review.constants import RESPONSE_CAP_BYTES
from btm_lit_review.corpus.paper import Paper, paper_from
from btm_lit_review.http import client


def fetch(
    source: str, query: str, limit: int, window: Window, offset: int
) -> tuple[list[Paper], int | None]:
    """One logged search's papers from rank `offset`; linear in the works the
    index returns."""
    found = search(
        INDEXES[source], client(), RESPONSE_CAP_BYTES, query, limit, window, offset
    )
    return list(map(paper_from, found.works)), found.total
