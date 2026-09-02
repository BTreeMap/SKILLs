"""The paper as searchable text: page index, anchor resolution, section spans.

One index per process, O(N) in the paper's length; every anchor lookup is
then O(len(quote)). Positions live in normalized coordinates, so a quote
copied from a PDF with odd whitespace, curly quotes, or ligatures still
resolves.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from btm_corekit import CommandError
from btm_peer_review.constants import (
    ANCHOR_COVERAGE,
    ANCHOR_GRAM,
    EMAIL,
    LIMITATIONS_HEADING,
    NON_WORD,
    PAGE_MARKER,
    SECTION_END,
    WHITESPACE,
)

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
    return WHITESPACE.sub(" ", text.translate(_TRANSLATE).lower()).strip()


def tokens(normalized: str) -> list[str]:
    return [w for w in NON_WORD.split(normalized) if w]


def parse_pages(raw: str) -> list[tuple[int, str]]:
    """`## PDF page N` markers split the extraction; none means one page."""
    markers = list(PAGE_MARKER.finditer(raw))
    if not markers:
        return [(1, raw)]
    pages = []
    for index, match in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(raw)
        pages.append((int(match.group(1)), raw[match.end() : end]))
    return pages


@dataclass(frozen=True, slots=True)
class Verbatim:
    page: int
    offset: int  # normalized coordinate of the hit


@dataclass(frozen=True, slots=True)
class Fuzzy:
    page: int
    offset: int
    coverage: float  # share of the quote's n-grams found, above the floor


@dataclass(frozen=True, slots=True)
class Unresolved:
    best_page: int | None
    coverage: float


Anchoring = Verbatim | Fuzzy | Unresolved


@dataclass(frozen=True, slots=True)
class Span:
    """A region in normalized coordinates: [start, end)."""

    start: int
    end: int

    def holds(self, offset: int) -> bool:
        return self.start <= offset < self.end


def _grams(toks: list[str]) -> list[tuple[str, ...]]:
    return [
        tuple(toks[i : i + ANCHOR_GRAM]) for i in range(len(toks) - ANCHOR_GRAM + 1)
    ]


class PaperText:
    """Immutable after construction; the index is the whole cost."""

    __slots__ = ("_index", "_starts", "full", "limitations", "numbers", "pages")

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
        # gram -> (page index, normalized offset of its first word); first wins
        self._index: dict[tuple[str, ...], tuple[int, int]] = {}
        for page_index, chunk in enumerate(normalized):
            base = self._starts[page_index]
            toks = tokens(chunk)
            starts = []
            position = 0
            for word in toks:
                position = chunk.find(word, position)
                starts.append(base + position)
                position += len(word)
            for i, gram in enumerate(_grams(toks)):
                self._index.setdefault(gram, (page_index, starts[i]))
        self.limitations = self._limitations_span()

    @classmethod
    def from_file(cls, path: Path) -> PaperText:
        if not path.is_file():
            raise CommandError(f"no paper text at {path}: run ingest first")
        return cls(parse_pages(path.read_text(encoding="utf-8")))

    def page_at(self, offset: int) -> int:
        return self.numbers[bisect_right(self._starts, offset) - 1]

    def resolve(self, quote: str) -> Anchoring:
        """Verbatim substring first; else n-gram coverage over the whole paper."""
        needle = normalize(quote)
        if not needle:
            return Unresolved(None, 0.0)
        position = self.full.find(needle)
        if position >= 0:
            return Verbatim(self.page_at(position), position)
        grams = _grams(tokens(needle))
        if not grams:
            return Unresolved(None, 0.0)
        hits = [self._index[gram] for gram in grams if gram in self._index]
        coverage = round(len(hits) / len(grams), 2)
        if not hits:
            return Unresolved(None, coverage)
        page_index = Counter(page for page, _ in hits).most_common(1)[0][0]
        offset = min(off for page, off in hits if page == page_index)
        page = self.numbers[page_index]
        if coverage >= ANCHOR_COVERAGE:
            return Fuzzy(page, offset, coverage)
        return Unresolved(page, coverage)

    def in_limitations(self, offset: int) -> bool:
        return self.limitations is not None and self.limitations.holds(offset)

    def author_block(self) -> bool:
        """Advisory: an email on the first page means the author block is in."""
        return bool(self.pages) and EMAIL.search(self.pages[0][1]) is not None

    def _limitations_span(self) -> Span | None:
        for page_index, (_, raw) in enumerate(self.pages):
            heading = LIMITATIONS_HEADING.search(raw)
            if heading is None:
                continue
            start = self._starts[page_index] + len(normalize(raw[: heading.end()]))
            for later_index in range(page_index, len(self.pages)):
                later_raw = self.pages[later_index][1]
                search_from = heading.end() if later_index == page_index else 0
                closing = SECTION_END.search(later_raw, search_from)
                if closing is not None:
                    end = self._starts[later_index] + len(
                        normalize(later_raw[: closing.start()])
                    )
                    return Span(start, end)
            return Span(start, len(self.full))
        return None
