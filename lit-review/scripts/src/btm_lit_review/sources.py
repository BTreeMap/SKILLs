"""One fetcher per upstream source, returning Papers and a reported total."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections.abc import Sequence

from btm_corekit import polite_params
from btm_lit_review.constants import (
    ARXIV_QUERY,
    ATOM,
    COURTESY_PAUSE_SECONDS,
    CROSSREF_WORKS,
    ID_BATCH_SIZE,
    OPENALEX_WORKS,
    OPENSEARCH,
)
from btm_lit_review.http import http_get, http_get_json, openalex_json
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
    filters = []
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    body = openalex_json(OPENALEX_WORKS, params)
    total = (body.get("meta") or {}).get("count") or 0
    return [paper_from_openalex(work) for work in body.get("results") or []], total


def fetch_openalex_by_ids(openalex_ids: Sequence[str]) -> list[Paper]:
    papers: list[Paper] = []
    for start in range(0, len(openalex_ids), ID_BATCH_SIZE):
        batch = openalex_ids[start : start + ID_BATCH_SIZE]
        params = {
            "filter": "openalex_id:" + "|".join(batch),
            "per-page": str(ID_BATCH_SIZE),
        }
        body = openalex_json(OPENALEX_WORKS, params)
        papers.extend(paper_from_openalex(w) for w in body.get("results") or [])
        time.sleep(COURTESY_PAUSE_SECONDS)
    return papers


def fetch_arxiv(query: str, limit: int) -> tuple[list[Paper], int]:
    search_query = query if ":" in query else f'all:"{query}"'
    params = {"search_query": search_query, "max_results": str(limit)}
    root = ET.fromstring(http_get(ARXIV_QUERY, params))
    total_node = root.find(OPENSEARCH + "totalResults")
    total = int(total_node.text) if total_node is not None and total_node.text else 0
    return [paper_from_arxiv(entry) for entry in root.findall(ATOM + "entry")], total


def fetch_crossref(
    query: str, limit: int, from_year: int | None, to_year: int | None
) -> tuple[list[Paper], int]:
    params = {"query": query, "rows": str(limit)}
    filters = []
    if from_year:
        filters.append(f"from-pub-date:{from_year}-01-01")
    if to_year:
        filters.append(f"until-pub-date:{to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    params |= polite_params()
    message = http_get_json(CROSSREF_WORKS, params).get("message") or {}
    total = message.get("total-results") or 0
    return [paper_from_crossref(item) for item in message.get("items") or []], total
