"""One fetcher per index, each returning Papers and the reported total.

Every index crosses into the kernel's `Work` first, so the projection into
a Paper is written once rather than once per source.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from btm_corekit import arxiv, crossref, openalex
from btm_lit_review.constants import COURTESY_PAUSE_SECONDS, RESPONSE_CAP_BYTES
from btm_lit_review.corpus.paper import Paper, paper_from
from btm_lit_review.http import client


def fetch_openalex(
    query: str, limit: int, from_year: int | None, to_year: int | None
) -> tuple[list[Paper], int]:
    params = {"search": query, "per-page": str(limit)}
    if window := openalex.year_filter(from_year, to_year):
        params["filter"] = window
    page = openalex.page(client(), RESPONSE_CAP_BYTES, params)
    return [paper_from(openalex.record(work)) for work in page.results], page.total or 0


def fetch_openalex_by_ids(openalex_ids: Sequence[str]) -> list[Paper]:
    papers: list[Paper] = []
    for batch in openalex.batched(openalex_ids):
        page = openalex.page(
            client(),
            RESPONSE_CAP_BYTES,
            {
                "filter": "openalex_id:" + "|".join(batch),
                "per-page": str(openalex.ID_BATCH_SIZE),
            },
        )
        papers.extend(paper_from(openalex.record(work)) for work in page.results)
        time.sleep(COURTESY_PAUSE_SECONDS)
    return papers


def fetch_arxiv(query: str, limit: int) -> tuple[list[Paper], int]:
    feed = arxiv.feed(client(), RESPONSE_CAP_BYTES, query, limit)
    return [paper_from(arxiv.record(entry)) for entry in feed.entries], feed.total or 0


def fetch_crossref(
    query: str, limit: int, from_year: int | None, to_year: int | None
) -> tuple[list[Paper], int]:
    params = {"query": query, "rows": str(limit)}
    if window := crossref.date_filter(from_year, to_year):
        params["filter"] = window
    message = crossref.page(client(), RESPONSE_CAP_BYTES, params)
    found = [paper_from(crossref.record(item)) for item in message.items]
    return found, message.total or 0
