"""Where the prose is: a text cut into blocks of segments, each segment a run
of characters whose sentences the splitter reads.

Masking keeps every length, so an offset into the masked text is an offset
into the source, and a line number follows from it. An inline code span
keeps its two backticks and blanks its inside: it counts as one word and no
word in it is checked. In Markdown, front matter and fenced code blank
out; each heading, list item, table row, and line that opens with a tag
starts a block; each table cell is a segment. One pass over lines, `str`
methods only: O(n).
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import accumulate, pairwise

from btm_corekit import CommandError, blanked


class Format(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"


Span = tuple[int, int]
Block = tuple[Span, ...]  # one paragraph: the segments its sentences come from

PARAGRAPH = re.compile(r"\n[ \t]*\n")
FENCES = ("```", "~~~")
TABLE_RULE = frozenset("|-: \t")
HEADING_MAX = 6
LIST_MARKS = ("- ", "* ", "+ ")
ORDINAL_DIGITS = 9


@dataclass(frozen=True, slots=True)
class Layout:
    masked: str
    blocks: tuple[Block, ...]
    line_starts: tuple[int, ...]

    def line(self, offset: int) -> int:
        """The 1-based line that holds `offset`."""
        return bisect_right(self.line_starts, offset)


def mask_code(text: str) -> str:
    """Blank a fenced span whole and the inside of an inline span. An inline
    span closes on its own line; a lone backtick stays as text."""
    pieces: list[str] = []
    position = cursor = 0
    while (start := text.find("`", cursor)) != -1:
        if text.startswith("```", start):
            end = text.find("```", start + 3)
            stop = len(text) if end == -1 else end + 3
            pieces += [text[position:start], blanked(text[start:stop])]
        else:
            end = text.find("`", start + 1)
            if end == -1 or text.find("\n", start, end) != -1:
                cursor = start + 1
                continue
            stop = end + 1
            pieces += [text[position:start], "`", " " * (end - start - 1), "`"]
        position = cursor = stop
    pieces.append(text[position:])
    return "".join(pieces)


def mask_markup(line: str) -> str:
    """Blank each tag (`<x ...>`, `</x>`) and each link target `](...)`."""
    pieces: list[str] = []
    position = cursor = 0
    while (start := line.find("<", cursor)) != -1:
        end = line.find(">", start + 1)
        nxt = line[start + 1 : start + 2]
        if end == -1 or not (nxt.isalpha() or nxt in "/!"):
            cursor = start + 1
            continue
        pieces += [line[position:start], " " * (end + 1 - start)]
        position = cursor = end + 1
    pieces.append(line[position:])
    line = "".join(pieces)
    pieces, position = [], 0
    while (start := line.find("](", position)) != -1:
        end = line.find(")", start + 2)
        if end == -1:
            break
        pieces += [line[position : start + 1], " " * (end - start)]
        position = end + 1
    pieces.append(line[position:])
    return "".join(pieces)


def starts(text: str) -> tuple[int, ...]:
    return tuple(accumulate((len(ln) + 1 for ln in text.split("\n")[:-1]), initial=0))


@dataclass(frozen=True, slots=True)
class Cut:
    """How to find the prose: the input format, and for Markdown the one
    heading whose section to keep."""

    fmt: Format = Format.TEXT
    section: str | None = None


def layout(text: str, cut: Cut) -> Layout:
    """The prose of `text`, cut by `cut.fmt`; `cut.section` keeps one
    Markdown heading and its lines, up to the next heading of any level."""
    masked = mask_code(text)
    line_starts = starts(masked)
    match cut.fmt:
        case Format.TEXT:
            if cut.section is not None:
                raise CommandError("--section needs --format markdown")
            return Layout(masked, paragraph_blocks(masked), line_starts)
        case Format.MARKDOWN:
            lines = masked.split("\n")
            scanner = Scanner(lines, text.split("\n"), line_starts, cut.section)
            return scanner.run()


def paragraph_blocks(text: str) -> tuple[Block, ...]:
    """Text format: a blank line ends a paragraph."""
    bounds = [0, *(i for m in PARAGRAPH.finditer(text) for i in m.span()), len(text)]
    return tuple(
        ((a, b),)
        for a, b in zip(bounds[::2], bounds[1::2], strict=True)
        if text[a:b].strip()
    )


def heading_of(stripped: str) -> tuple[int, str] | None:
    level = len(stripped) - len(stripped.lstrip("#"))
    if 0 < level <= HEADING_MAX and stripped[level : level + 1] in ("", " "):
        return level, stripped[level:].strip()
    return None


def item_mark(stripped: str) -> int:
    """Width of a list marker and its space, or 0 when the line has none."""
    if stripped.startswith(LIST_MARKS):
        return 2
    digits = len(stripped[: ORDINAL_DIGITS + 1]) - len(
        stripped[: ORDINAL_DIGITS + 1].lstrip("0123456789")
    )
    if 0 < digits <= ORDINAL_DIGITS and stripped[digits : digits + 2] in (". ", ") "):
        return digits + 2
    return 0


@dataclass(slots=True)
class Scanner:
    """One pass over Markdown lines; `out` is the masked copy. A heading's
    title comes from `source`, so a code span in it can be named."""

    lines: list[str]
    source: list[str]
    line_starts: tuple[int, ...]
    section: str | None
    out: list[str] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    current: list[Span] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    waiting: str | None = None  # what closes a skipped region
    inside: bool = False  # within the kept section

    def run(self) -> Layout:
        self.out = list(self.lines)
        for n, line in enumerate(self.lines):
            if self.skipped(n, line.strip()):
                self.out[n] = blanked(line)
            else:
                self.prose(n, mask_markup(line))
        self.close()
        wanted = self.section
        if wanted is not None and wanted.lower() not in map(str.lower, self.headings):
            raise CommandError(
                f"--section {wanted!r} names no heading; "
                f"headings: {', '.join(self.headings)}"
            )
        return Layout("\n".join(self.out), tuple(self.blocks), self.line_starts)

    def close(self) -> None:
        if self.current:
            self.blocks.append(tuple(self.current))
            self.current.clear()

    def skipped(self, n: int, stripped: str) -> bool:
        """Front matter, a fence, or a line outside the section."""
        if self.waiting is not None:
            if stripped.startswith(self.waiting) or self.waiting in stripped:
                self.waiting = None
            return True
        if n == 0 and stripped == "---":
            self.waiting = "---"
            return True
        if stripped.startswith(FENCES):
            self.close()
            self.waiting = stripped[:3]
            return True
        heading = heading_of(self.source[n].strip())
        if heading is not None:
            self.close()
            self.headings.append(heading[1])
            wanted = self.section or ""
            self.inside = heading[1].lower() == wanted.lower()
        return self.section is not None and not self.inside

    def prose(self, n: int, line: str) -> None:
        self.out[n] = line
        at = self.line_starts[n]
        stripped = line.strip()
        lead = len(line) - len(line.lstrip())
        if not stripped:
            self.close()
        elif heading_of(stripped) is not None:
            mark = lead + len(stripped) - len(stripped.lstrip("#"))
            self.blocks.append(((at + mark, at + len(line)),))
        elif stripped.startswith("|"):
            self.close()
            if not set(stripped) <= TABLE_RULE:
                cells = pairwise(pipes(line))
                row = [
                    (at + a + 1, at + b) for a, b in cells if line[a + 1 : b].strip()
                ]
                self.blocks.append(tuple(row))
        elif (mark := item_mark(stripped)) or stripped.startswith("<"):
            self.close()
            self.current.append((at + lead + mark, at + len(line)))
        elif self.current:
            self.current[-1] = (self.current[-1][0], at + len(line))
        else:
            self.current.append((at, at + len(line)))


def pipes(line: str) -> list[int]:
    """Offsets of every `|`; a pipe inside code was masked away."""
    out: list[int] = []
    while (i := line.find("|", out[-1] + 1 if out else 0)) != -1:
        out.append(i)
    return out
