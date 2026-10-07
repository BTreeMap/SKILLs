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

import re
from typing import Annotated, Any

from pydantic import BeforeValidator

from btm_corekit.records.models import DOI_PATTERN, ArxivId, Count, Doi, Model
from btm_corekit.text import collapse_whitespace, is_digits

DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")
DOI = re.compile(DOI_PATTERN)
"""The `Doi` pattern itself, so absence and admission cannot disagree: one
class per quantifier, linear in the backtracking engine."""

ARXIV_NUMBER_WIDTHS = (5, 4)
"""New-scheme numbers: `YYMM.NNNNN`, and `YYMM.NNNN` before 2015."""

ARXIV_OLD_NUMBER_WIDTH = 7
"""Old-scheme numbers: `archive/YYMMNNN`, with an optional `.SC` subject class."""

ARXIV_ARCHIVES = frozenset(
    {
        "acc-phys",
        "adap-org",
        "alg-geom",
        "ao-sci",
        "astro-ph",
        "atom-ph",
        "bayes-an",
        "chao-dyn",
        "chem-ph",
        "cmp-lg",
        "comp-gas",
        "cond-mat",
        "cs",
        "dg-ga",
        "funct-an",
        "gr-qc",
        "hep-ex",
        "hep-lat",
        "hep-ph",
        "hep-th",
        "math",
        "math-ph",
        "mtrl-th",
        "nlin",
        "nucl-ex",
        "nucl-th",
        "patt-sol",
        "physics",
        "plasm-ph",
        "q-alg",
        "q-bio",
        "quant-ph",
        "solv-int",
        "supr-con",
    }
)
"""Every archive that issued old-scheme ids; a URL ending in `word/NNNNNNN`
with any other word is some other site's path."""

ARXIV_MARKERS = ("arxiv:", "arxiv.")
"""What precedes a bare id in a citation (`arXiv:hep-th/9901001`) and in the
registered DOI (`10.48550/arXiv.hep-th/9901001`), compared case-folded."""

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
    return doi if DOI.match(doi) else None


def _arxiv(raw: Any) -> Any:
    """The arXiv id ending the text, either scheme, version and `.pdf` dropped,
    whatever precedes it ignored: the bare id, `arXiv:` prefix, abs or pdf URL,
    or the registered DOI. Unparseable is absence."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.lower().endswith(".pdf"):
        text = text[: -len(".pdf")]
    head, marker, version = text.rpartition("v")
    if marker and is_digits(version):
        text = head
    return _new_scheme(text) or _old_scheme(text)


def _new_scheme(text: str) -> str | None:
    """`YYMM.NNNNN` or `YYMM.NNNN` at the end of `text`."""
    for width in ARXIV_NUMBER_WIDTHS:
        tail = text[-(1 + 4 + width) :]
        if (
            len(tail) == 1 + 4 + width
            and is_digits(tail[:4])
            and tail[4] == "."
            and is_digits(tail[5:])
        ):
            return tail
    return None


def _old_scheme(text: str) -> str | None:
    """`archive/NNNNNNN` or `archive.SC/NNNNNNN` at the end of `text`, the
    archive one of arXiv's own and lowercased, the subject class as written."""
    head, slash, number = text.rpartition("/")
    if not slash or len(number) != ARXIV_OLD_NUMBER_WIDTH or not is_digits(number):
        return None
    segment = head.rpartition("/")[2]
    for prefix in ARXIV_MARKERS:
        if segment.lower().startswith(prefix):
            segment = segment[len(prefix) :]
    archive, dot, subject = segment.partition(".")
    archive = archive.lower()
    if archive not in ARXIV_ARCHIVES or (dot and not _is_subject_class(subject)):
        return None
    return f"{archive}{dot}{subject}/{number}"


def _is_subject_class(word: str) -> bool:
    """Letters and hyphens, non-empty: `GT`, `optics`, `dis-nn`."""
    letters = word.replace("-", "")
    return bool(letters) and letters.isascii() and letters.isalpha()


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
