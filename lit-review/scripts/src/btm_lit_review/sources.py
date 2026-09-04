"""One fetcher per index, returning Papers and the reported total."""

from __future__ import annotations

import time
from collections.abc import Sequence

from btm_corekit import (
    arxiv_feed,
    batched,
    crossref_filter,
    crossref_page,
    openalex_page,
    year_filter,
)
from btm_lit_review.constants import (
    COURTESY_PAUSE_SECONDS,
    ID_BATCH_SIZE,
    RESPONSE_CAP_BYTES,
)
from btm_lit_review.http import client
from btm_lit_review.paper import Paper
from btm_lit_review.upstream import (
    paper_from_arxiv,
    paper_from_crossref,
    paper_from_openalex,
)


def fetch_openalex(
    query: str, limit: int, from_year: int | None, to_year: int | None
) -> tuple[list[Paper], int]:
    params = {"search": query, "per-page": str(limit)}
    if window := year_filter(from_year, to_year):
        params["filter"] = window
    page = openalex_page(client(), RESPONSE_CAP_BYTES, params)
    return [paper_from_openalex(work) for work in page.results], page.meta.count


def fetch_openalex_by_ids(openalex_ids: Sequence[str]) -> list[Paper]:
    papers: list[Paper] = []
    for batch in batched(openalex_ids, ID_BATCH_SIZE):
        page = openalex_page(
            client(),
            RESPONSE_CAP_BYTES,
            {
                "filter": "openalex_id:" + "|".join(batch),
                "per-page": str(ID_BATCH_SIZE),
            },
        )
        papers.extend(paper_from_openalex(work) for work in page.results)
        time.sleep(COURTESY_PAUSE_SECONDS)
    return papers


def fetch_arxiv(query: str, limit: int) -> tuple[list[Paper], int]:
    feed = arxiv_feed(client(), RESPONSE_CAP_BYTES, query, limit)
    return [paper_from_arxiv(entry) for entry in feed.entries], feed.total


def fetch_crossref(
    query: str, limit: int, from_year: int | None, to_year: int | None
) -> tuple[list[Paper], int]:
    params = {"query": query, "rows": str(limit)}
    if window := crossref_filter(from_year, to_year):
        params["filter"] = window
    message = crossref_page(client(), RESPONSE_CAP_BYTES, params)
    return [paper_from_crossref(item) for item in message.items], message.total
