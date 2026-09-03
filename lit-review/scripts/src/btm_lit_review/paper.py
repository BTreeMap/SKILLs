"""The Paper record: identity, normalization, merging, and the parse boundary."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, fields, replace
from typing import Any

from btm_corekit import CommandError, ascii_words, collapse_whitespace, is_digits
from btm_lit_review.constants import READ_LEVELS, STATUSES


@dataclass(frozen=True, slots=True)
class Paper:
    """One deduplicated bibliographic record in the session corpus."""

    key: str
    title: str
    year: int | None
    authors: tuple[str, ...]
    venue: str | None
    doi: str | None
    arxiv_id: str | None
    openalex_id: str | None
    cited_by_count: int | None
    abstract: str | None
    pdf_url: str | None
    landing_url: str | None
    found_by: tuple[str, ...]
    status: str
    decision_reason: str | None
    read_level: str


def clean_text(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    return collapse_whitespace(raw) or None


def normalize_doi(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    doi = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        doi = doi.removeprefix(prefix)
    return doi if doi.startswith("10.") else None


def normalize_arxiv_id(raw: object) -> str | None:
    """The `YYMM.NNNNN` (or `YYMM.NNNN`) id ending the text, an optional
    `vN` suffix dropped, whatever precedes it (a URL, `arXiv:`)."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    head, v, version = text.rpartition("v")
    if v and is_digits(version):
        text = head
    for width in (5, 4):
        tail = text[-(5 + width) :]
        if (
            len(tail) == 5 + width
            and is_digits(tail[:4])
            and tail[4] == "."
            and is_digits(tail[5:])
        ):
            return tail
    return None


def normalize_title(title: str) -> str:
    return " ".join(ascii_words(title))


def paper_key(doi: str | None, arxiv_id: str | None, title: str) -> str:
    if doi:
        return f"doi:{doi}"
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    return f"title:{normalize_title(title)}"


def paper_aliases(paper: Paper) -> Iterator[str]:
    if paper.doi:
        yield f"doi:{paper.doi}"
    if paper.arxiv_id:
        yield f"arxiv:{paper.arxiv_id}"
    yield f"title:{normalize_title(paper.title)}"


def candidate(**bibliographic: Any) -> Paper:
    """Smart constructor: derive the key, start unscreened."""
    doi = bibliographic.get("doi")
    arxiv_id = bibliographic.get("arxiv_id")
    title = bibliographic["title"]
    return Paper(
        key=paper_key(doi, arxiv_id, title),
        found_by=(),
        status="candidate",
        decision_reason=None,
        read_level="none",
        **bibliographic,
    )


def merge_papers(existing: Paper, incoming: Paper) -> Paper:
    """Bibliographic fields fill gaps; agent-owned decisions never move."""
    updates: dict[str, Any] = {}
    for name in (
        "year",
        "venue",
        "doi",
        "arxiv_id",
        "openalex_id",
        "abstract",
        "pdf_url",
        "landing_url",
    ):
        if getattr(existing, name) is None:
            updates[name] = getattr(incoming, name)
    counts = (existing.cited_by_count, incoming.cited_by_count)
    known_counts = [count for count in counts if count is not None]
    updates["cited_by_count"] = max(known_counts) if known_counts else None
    fresh = tuple(x for x in incoming.found_by if x not in existing.found_by)
    updates["found_by"] = existing.found_by + fresh
    return replace(existing, **updates)


def absorb(
    papers: dict[str, Paper], fetched: Iterable[Paper]
) -> tuple[dict[str, Paper], int]:
    """Fold fetched papers into the corpus; O(corpus + fetched)."""
    index = {
        alias: key for key, paper in papers.items() for alias in paper_aliases(paper)
    }
    result = dict(papers)
    new_count = 0
    for paper in fetched:
        hit = next((index[a] for a in paper_aliases(paper) if a in index), None)
        if hit is None:
            result[paper.key] = paper
            new_count += 1
            hit = paper.key
        else:
            result[hit] = merge_papers(result[hit], paper)
        for alias in paper_aliases(result[hit]):
            index.setdefault(alias, hit)
    return result, new_count


PAPER_FIELDS = frozenset(f.name for f in fields(Paper))
PAPER_DEFAULTS: dict[str, Any] = {
    "year": None,
    "authors": (),
    "venue": None,
    "doi": None,
    "arxiv_id": None,
    "openalex_id": None,
    "cited_by_count": None,
    "abstract": None,
    "pdf_url": None,
    "landing_url": None,
    "found_by": (),
    "status": "candidate",
    "decision_reason": None,
    "read_level": "none",
}


def paper_from_json(row: Mapping[str, Any]) -> Paper:
    """Parse boundary for state on disk; total: rejects corrupt records."""
    unknown = sorted(set(row) - PAPER_FIELDS)
    data = PAPER_DEFAULTS | dict(row)
    missing = sorted(PAPER_FIELDS - set(data))
    if unknown or missing:
        raise CommandError(
            f"corrupt paper record for key {row.get('key')!r}: "
            f"unknown fields {unknown}, missing fields {missing}"
        )
    if data["status"] not in STATUSES or data["read_level"] not in READ_LEVELS:
        raise CommandError(f"corrupt paper record for key {row.get('key')!r}")
    data["authors"] = tuple(data.get("authors") or ())
    data["found_by"] = tuple(data.get("found_by") or ())
    return Paper(**data)
