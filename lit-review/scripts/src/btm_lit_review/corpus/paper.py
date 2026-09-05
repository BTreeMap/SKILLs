"""The Paper record: identity, normalization, merging, and the parse boundary."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from pydantic import model_validator

from btm_corekit import (
    MaybeArxivId,
    MaybeDoi,
    Model,
    Work,
    ascii_words,
    parse_model,
)
from btm_lit_review.constants import ReadLevel, Status


class Paper(Model):
    """One deduplicated bibliographic record in the session corpus."""

    key: str
    title: str
    year: int | None = None
    authors: tuple[str, ...] = ()
    venue: str | None = None
    doi: MaybeDoi = None
    arxiv_id: MaybeArxivId = None
    openalex_id: str | None = None
    cited_by_count: int | None = None
    abstract: str | None = None
    pdf_url: str | None = None
    landing_url: str | None = None
    found_by: tuple[str, ...] = ()
    status: Status = Status.CANDIDATE
    decision_reason: str | None = None
    read_level: ReadLevel = ReadLevel.NONE

    @model_validator(mode="after")
    def _an_exclusion_carries_its_reason(self) -> Paper:
        # The write paths hold this too; the read path must, or a hand-edited
        # corpus breaks the report's flow counts in silence.
        if self.status is Status.EXCLUDED and not self.decision_reason:
            raise ValueError("an excluded paper carries the reason it was cut")
        return self


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


def paper_from(work: Work) -> Paper:
    """Smart constructor: one crossed index record becomes one unscreened
    candidate, its key derived from whichever identifier it carries. Every
    field is named, so a field added to either record is a type error here
    rather than a value silently dropped."""
    title = work.names
    return Paper(
        key=paper_key(work.doi, work.arxiv_id, title),
        title=title,
        year=work.year,
        authors=work.authors,
        venue=work.venue,
        doi=work.doi,
        arxiv_id=work.arxiv_id,
        openalex_id=work.openalex_id,
        cited_by_count=work.cited_by,
        abstract=work.abstract,
        pdf_url=work.pdf_url,
        landing_url=work.landing_url,
        found_by=(),
        status=Status.CANDIDATE,
        decision_reason=None,
        read_level=ReadLevel.NONE,
    )


def merge_papers(existing: Paper, incoming: Paper) -> Paper:
    """Bibliographic fields fill gaps; agent-owned decisions never move."""
    updates: dict[str, Any] = {
        name: getattr(incoming, name)
        for name in GAP_FILLABLE
        if getattr(existing, name) is None
    }
    counts = (existing.cited_by_count, incoming.cited_by_count)
    known_counts = [count for count in counts if count is not None]
    updates["cited_by_count"] = max(known_counts) if known_counts else None
    fresh = tuple(x for x in incoming.found_by if x not in existing.found_by)
    updates["found_by"] = existing.found_by + fresh
    return existing.with_(**updates)


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


PAPER_FIELDS = frozenset(Paper.model_fields)
IDENTITY_FIELDS = frozenset({"key", "title"})
DECISION_FIELDS = frozenset({"status", "decision_reason", "read_level"})
COUNTED_FIELDS = frozenset({"cited_by_count", "found_by", "authors"})
# Derived, so a field added to Paper cannot be left out of a merge.
GAP_FILLABLE = tuple(
    sorted(PAPER_FIELDS - IDENTITY_FIELDS - DECISION_FIELDS - COUNTED_FIELDS)
)


def paper_from_json(row: Mapping[str, Any]) -> Paper:
    """Parse boundary for state on disk; total, and located on the field."""
    return parse_model(Paper, row, f"corrupt paper record for key {row.get('key')!r}")
