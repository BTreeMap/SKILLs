"""The paper as searchable text: page index, anchor resolution, section spans.

Opening a paper normalizes each page in C and records where it begins, so
construction touches no character from Python. A verbatim anchor then costs
one `str.find`; a corrupted one costs one bit-parallel alignment inside
rapidfuzz. Positions live in normalized coordinates, so a quote copied from
a PDF with odd whitespace, curly quotes, or ligatures still resolves.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

from btm_corekit import CommandError, collapse_whitespace, heading_words
from btm_peer_review.constants import (
    ANCHOR_CHARS_MIN,
    ANCHOR_HINT_FLOOR,
    ANCHOR_SIMILARITY,
    LIMITATIONS_HEADINGS,
    PAGE_MARKER,
    SECTION_END_FIRST_WORDS,
    SECTION_END_PAIRS,
)

_MAIL_LOCAL = frozenset("._+-")
_MAIL_LABEL = frozenset("-_")

_TRANSLATE = str.maketrans(
    {
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u00ad": "",  # soft hyphen
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\u00a0": " ",  # no-break space
    }
)


def normalize(text: str) -> str:
    return collapse_whitespace(text.translate(_TRANSLATE).lower())


def page_marker(line: str) -> int | None:
    """The page number of a `## PDF page N` line, else None."""
    rest = line.removeprefix(PAGE_MARKER).strip()
    return int(rest) if line.startswith(PAGE_MARKER) and rest.isdigit() else None


def parse_pages(raw: str) -> list[tuple[int, str]]:
    """`## PDF page N` lines split the extraction; none means one page.
    One pass over the lines."""
    pages: list[tuple[int, list[str]]] = []
    for line in raw.split("\n"):
        number = page_marker(line)
        if number is not None:
            pages.append((number, []))
        elif pages:
            pages[-1][1].append(line)
    if not pages:
        return [(1, raw)]
    return [(number, "\n".join(lines)) for number, lines in pages]


def has_email(text: str) -> bool:
    """Whether an `x@label.tld` token occurs: one scan around each `@`."""
    at = text.find("@")
    while at != -1:
        if at > 0 and (text[at - 1].isalnum() or text[at - 1] in _MAIL_LOCAL):
            end = at + 1
            while end < len(text) and (text[end].isalnum() or text[end] in _MAIL_LABEL):
                end += 1
            if end > at + 1 and text[end : end + 1] == "." and text[end + 1 : end + 2]:
                after = text[end + 1]
                if after.isalnum() or after == "_":
                    return True
        at = text.find("@", at + 1)
    return False


def is_limitations_heading(line: str) -> bool:
    return tuple(heading_words(line)) in LIMITATIONS_HEADINGS


def is_section_end(line: str) -> bool:
    words = heading_words(line)
    if not words:
        return False
    return (
        words[0] in SECTION_END_FIRST_WORDS
        or words[0].startswith("acknowledg")
        or tuple(words[:2]) in SECTION_END_PAIRS
    )


@dataclass(frozen=True, slots=True)
class Verbatim:
    page: int
    offset: int  # normalized coordinate of the hit


@dataclass(frozen=True, slots=True)
class Fuzzy:
    page: int
    offset: int
    similarity: float  # best-substring similarity, at or above the floor


@dataclass(frozen=True, slots=True)
class Unresolved:
    best_page: int | None
    similarity: float


Anchoring = Verbatim | Fuzzy | Unresolved


@dataclass(frozen=True, slots=True)
class Span:
    """A region in normalized coordinates: [start, end)."""

    start: int
    end: int

    def holds(self, offset: int) -> bool:
        return self.start <= offset < self.end


class PaperText:
    """Immutable after construction: the normalized text and where its pages
    begin. Construction is one C-level normalization per page, so opening a
    30-page paper costs milliseconds and no per-word Python iteration."""

    __slots__ = ("_starts", "full", "limitations", "numbers", "pages")

    def __init__(self, pages: list[tuple[int, str]]) -> None:
        self.pages = tuple(pages)
        self.numbers = tuple(number for number, _ in pages)
        normalized = [normalize(text) for _, text in pages]
        self._starts: list[int] = []
        offset = 0
        for chunk in normalized:
            self._starts.append(offset)
            offset += len(chunk) + 1
        self.full = "\n".join(normalized)
        self.limitations = self._limitations_span()

    @classmethod
    def from_file(cls, path: Path) -> PaperText:
        if not path.is_file():
            raise CommandError(f"no paper text at {path}: run ingest first")
        return cls(parse_pages(path.read_text(encoding="utf-8")))

    def page_at(self, offset: int) -> int:
        return self.numbers[bisect_right(self._starts, offset) - 1]

    def resolve(self, quote: str) -> Anchoring:
        """Verbatim substring first, which is one C-level scan; else the best
        matching span by normalized indel similarity, which rapidfuzz finds
        with bit-parallel alignment and reports with its position."""
        needle = normalize(quote)
        if not needle:
            return Unresolved(None, 0.0)
        position = self.full.find(needle)
        if position >= 0:
            return Verbatim(self.page_at(position), position)
        if len(needle) < ANCHOR_CHARS_MIN:
            return Unresolved(None, 0.0)
        best = fuzz.partial_ratio_alignment(
            needle, self.full, score_cutoff=ANCHOR_HINT_FLOOR * 100
        )
        if best is None:
            return Unresolved(None, 0.0)
        similarity = round(best.score / 100, 2)
        page = self.page_at(best.dest_start)
        if similarity >= ANCHOR_SIMILARITY:
            return Fuzzy(page, best.dest_start, similarity)
        return Unresolved(page, similarity)

    def in_limitations(self, offset: int) -> bool:
        return self.limitations is not None and self.limitations.holds(offset)

    def author_block(self) -> bool:
        """Advisory: an email on the first page means the author block is in."""
        return bool(self.pages) and has_email(self.pages[0][1])

    def _lines(self) -> Iterator[tuple[int, int, int, str]]:
        """(page index, raw start, raw end, line) for every line, in order."""
        for page_index, (_, raw) in enumerate(self.pages):
            offset = 0
            for line in raw.split("\n"):
                yield page_index, offset, offset + len(line), line
                offset += len(line) + 1

    def _at(self, page_index: int, raw_offset: int) -> int:
        """Normalized coordinate of a raw offset within a page."""
        return self._starts[page_index] + len(
            normalize(self.pages[page_index][1][:raw_offset])
        )

    def _limitations_span(self) -> Span | None:
        """One pass over the lines: the first Limitations heading opens the
        span; the next section-ending heading closes it."""
        start: int | None = None
        for page_index, begin, end, line in self._lines():
            if start is None:
                if is_limitations_heading(line):
                    start = self._at(page_index, end)
            elif is_section_end(line):
                return Span(start, self._at(page_index, begin))
        return None if start is None else Span(start, len(self.full))
