"""The record every index crosses into, and the smart constructors that
make its guarantees true.

This is the far side of the tolerance boundary. A `Work` field is either a
value of the shape its type names or `None`, and nothing in between: no
empty string standing in for a title, no zero standing in for a count, no
unparseable string standing in for a DOI. Each field's coercion lives on
the field, so a crossing states what the index knew and the guarantees hold
without three decoders remembering the same rule.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BeforeValidator

from btm_corekit.records.models import ArxivId, Count, Doi, Model
from btm_corekit.text import collapse_whitespace, is_digits

DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")

ARXIV_ID_WIDTHS = (5, 4)
"""arXiv numbers a paper `YYMM.NNNNN`, and `YYMM.NNNN` before 2015."""

EARLIEST_YEAR = 1000
LATEST_YEAR = 2999

ISO_DATE_LENGTH = 10


def collapsed(raw: str | None) -> str | None:
    """Collapsed text, or None where nothing survives. An index sends an
    empty string for a field it has no value for as readily as it omits it."""
    return collapse_whitespace(raw).strip() or None if raw else None


def _doi(raw: Any) -> Any:
    """An unparseable DOI is absence, not a rejection: indexes return junk in
    this field and the rest of the record is still worth keeping."""
    if not isinstance(raw, str):
        return None
    doi = raw.strip().lower()
    for prefix in DOI_PREFIXES:
        doi = doi.removeprefix(prefix)
    return doi if doi.startswith("10.") else None


def _arxiv(raw: Any) -> Any:
    """The `YYMM.NNNNN` id ending the text, an optional `vN` dropped, whatever
    precedes it ignored. That covers every written form one arrives in: the
    bare id, `arXiv:2401.01234`, `https://arxiv.org/abs/2401.01234v2`, and the
    registered DOI `10.48550/arXiv.2401.01234`, which is where OpenAlex now
    carries it. Unparseable is absence."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    head, marker, version = text.rpartition("v")
    if marker and is_digits(version):
        text = head
    for width in ARXIV_ID_WIDTHS:
        tail = text[-(1 + 4 + width) :]
        if (
            len(tail) == 1 + 4 + width
            and is_digits(tail[:4])
            and tail[4] == "."
            and is_digits(tail[5:])
        ):
            return tail
    return None


def _year(raw: Any) -> Any:
    """A year outside every plausible publication is absence. Crossref returns
    a date part of null and an occasional 0; neither is a year to print."""
    if not isinstance(raw, int) or isinstance(raw, bool):
        return None
    return raw if EARLIEST_YEAR <= raw <= LATEST_YEAR else None


def _count(raw: Any) -> Any:
    """A negative count is absence rather than a rejection: the rest of the
    record still stands."""
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return raw


def _iso_date(raw: Any) -> Any:
    """The date at the head of a timestamp. arXiv stamps a full
    `2024-01-05T00:00:00Z`; only the day is a fact about the paper."""
    if not isinstance(raw, str):
        return None
    head = raw.strip()[:ISO_DATE_LENGTH]
    fits = (
        len(head) == ISO_DATE_LENGTH
        and is_digits(head[:4])
        and head[4] == "-"
        and is_digits(head[5:7])
        and head[7] == "-"
        and is_digits(head[8:])
    )
    return head if fits else None


MaybeDoi = Annotated[Doi | None, BeforeValidator(_doi)]
MaybeArxivId = Annotated[ArxivId | None, BeforeValidator(_arxiv)]
MaybeYear = Annotated[int | None, BeforeValidator(_year)]
MaybeCount = Annotated[Count | None, BeforeValidator(_count)]
MaybeIsoDate = Annotated[str | None, BeforeValidator(_iso_date)]

normalize_doi = _doi
normalize_arxiv_id = _arxiv


class Work(Model):
    """One bibliographic record as this library knows it, whichever index it
    came from. Every field is required at construction so a new index cannot
    quietly know less than the others; what it does not know, it says."""

    title: str | None
    authors: tuple[str, ...]
    year: MaybeYear
    venue: str | None
    doi: MaybeDoi
    arxiv_id: MaybeArxivId
    openalex_id: str | None
    cited_by: MaybeCount
    abstract: str | None
    pdf_url: str | None
    landing_url: str | None
    published: MaybeIsoDate

    @property
    def names(self) -> str:
        """The title an agent should show, absence included."""
        return self.title or "(untitled)"
