"""Normalizing one upstream record into a Paper, per source."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from typing import Any

from btm_lit_review.constants import ARXIV_NS, ATOM, JATS_TAG
from btm_lit_review.paper import (
    Paper,
    candidate,
    clean_text,
    normalize_arxiv_id,
    normalize_doi,
)


def reconstruct_abstract(inverted: Mapping[str, Sequence[int]] | None) -> str | None:
    if not inverted:
        return None
    positions = sorted(
        (position, word) for word, places in inverted.items() for position in places
    )
    return " ".join(word for _, word in positions) or None


def paper_from_openalex(work: Mapping[str, Any]) -> Paper:
    ids = work.get("ids") or {}
    source = (work.get("primary_location") or {}).get("source") or {}
    openalex_url = work.get("id") or ""
    return candidate(
        title=clean_text(work.get("display_name")) or "(untitled)",
        year=work.get("publication_year"),
        authors=tuple(
            name
            for name in (
                clean_text((entry.get("author") or {}).get("display_name"))
                for entry in work.get("authorships") or []
            )
            if name
        ),
        venue=clean_text(source.get("display_name")),
        doi=normalize_doi(work.get("doi")),
        arxiv_id=normalize_arxiv_id(str(ids.get("arxiv") or "")),
        openalex_id=openalex_url.rsplit("/", 1)[-1] or None,
        cited_by_count=work.get("cited_by_count"),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        pdf_url=(work.get("open_access") or {}).get("oa_url"),
        landing_url=work.get("doi") or openalex_url or None,
    )


def paper_from_arxiv(entry: ET.Element) -> Paper:
    def text(tag: str) -> str | None:
        node = entry.find(ATOM + tag)
        return clean_text(node.text) if node is not None else None

    pdf_url = next(
        (
            link.get("href")
            for link in entry.findall(ATOM + "link")
            if link.get("title") == "pdf"
        ),
        None,
    )
    doi_node = entry.find(ARXIV_NS + "doi")
    published = text("published") or ""
    return candidate(
        title=text("title") or "(untitled)",
        year=int(published[:4]) if published[:4].isdigit() else None,
        authors=tuple(
            clean_text(node.text) or ""
            for node in entry.findall(f"{ATOM}author/{ATOM}name")
            if clean_text(node.text)
        ),
        venue=text("journal_ref"),
        doi=normalize_doi(doi_node.text if doi_node is not None else None),
        arxiv_id=normalize_arxiv_id(text("id") or ""),
        openalex_id=None,
        cited_by_count=None,
        abstract=text("summary"),
        pdf_url=pdf_url,
        landing_url=text("id"),
    )


def paper_from_crossref(item: Mapping[str, Any]) -> Paper:
    authors = tuple(
        name
        for name in (
            clean_text(f"{a.get('given', '')} {a.get('family', '')}")
            for a in item.get("author") or []
        )
        if name
    )
    issued = (item.get("issued") or {}).get("date-parts") or [[None]]
    abstract_raw = item.get("abstract")
    abstract = clean_text(JATS_TAG.sub(" ", abstract_raw)) if abstract_raw else None
    return candidate(
        title=clean_text(" ".join(item.get("title") or [])) or "(untitled)",
        year=issued[0][0] if issued[0] else None,
        authors=authors,
        venue=clean_text(" ".join(item.get("container-title") or [])),
        doi=normalize_doi(item.get("DOI")),
        arxiv_id=None,
        openalex_id=None,
        cited_by_count=item.get("is-referenced-by-count"),
        abstract=abstract,
        pdf_url=None,
        landing_url=item.get("URL"),
    )
