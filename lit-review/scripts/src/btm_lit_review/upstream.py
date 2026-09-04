"""Projecting an index record into a Paper."""

from __future__ import annotations

from btm_corekit import ArxivEntry, CrossrefItem, OpenAlexWork, is_digits, strip_tags
from btm_lit_review.paper import (
    Paper,
    candidate,
    clean_text,
    normalize_arxiv_id,
    normalize_doi,
)


def paper_from_openalex(work: OpenAlexWork) -> Paper:
    return candidate(
        title=clean_text(work.display_name) or "(untitled)",
        year=work.publication_year,
        authors=tuple(name for name in map(clean_text, work.authors) if name),
        venue=clean_text(work.primary_location.source.display_name),
        doi=normalize_doi(work.doi),
        arxiv_id=normalize_arxiv_id(work.ids.arxiv),
        openalex_id=work.key or None,
        cited_by_count=work.cited_by_count,
        abstract=clean_text(work.abstract),
        pdf_url=work.open_access.oa_url,
        landing_url=work.doi or work.id or None,
    )


def paper_from_arxiv(entry: ArxivEntry) -> Paper:
    return candidate(
        title=clean_text(entry.title) or "(untitled)",
        year=int(entry.published[:4]) if is_digits(entry.published[:4]) else None,
        authors=tuple(name for name in map(clean_text, entry.authors) if name),
        venue=clean_text(entry.journal_ref),
        doi=normalize_doi(entry.doi),
        arxiv_id=normalize_arxiv_id(entry.id),
        openalex_id=None,
        cited_by_count=None,
        abstract=clean_text(entry.summary),
        pdf_url=entry.pdf_url,
        landing_url=entry.id or None,
    )


def paper_from_crossref(item: CrossrefItem) -> Paper:
    """Crossref abstracts arrive as JATS markup."""
    return candidate(
        title=clean_text(" ".join(item.title)) or "(untitled)",
        year=item.issued.year,
        authors=tuple(name for name in map(clean_text, item.authors) if name),
        venue=clean_text(" ".join(item.container_title)),
        doi=normalize_doi(item.doi),
        arxiv_id=None,
        openalex_id=None,
        cited_by_count=item.cited_by,
        abstract=clean_text(strip_tags(item.abstract, " ")) if item.abstract else None,
        pdf_url=None,
        landing_url=item.url or None,
    )
