"""Markdown structure: the regions a compression must leave untouched."""

from __future__ import annotations

import re
from collections import Counter

FRONTMATTER_REGEX = re.compile(r"\A(---\r?\n.*?\r?\n---\r?\n)(.*)", re.DOTALL)
FENCE_OPEN_REGEX = re.compile(r"^(\s{0,3})(`{3,}|~{3,})(.*)$")
# CommonMark ATX: 0-3 spaces of indent, 1-6 '#', then space/tab (never a
# newline) or end of line; empty headings are legal.
ATX_HEADING_REGEX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
# CommonMark setext underline: a run of '=' (level 1) or '-' (level 2)
# directly under a paragraph line.
SETEXT_UNDERLINE_REGEX = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
INDENTED_LINE_REGEX = re.compile(r"^(?: {4,}|\t)")
LIST_ITEM_REGEX = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])[ \t]")
BULLET_REGEX = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
URL_REGEX = re.compile(r"https?://[^\s)]+")
PATH_REGEX = re.compile(
    r"(?:\./|\.\./|/|[A-Za-z]:\\)[\w\-/\\.]+|[\w\-.]+[/\\][\w\-/\\.]+"
)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Partition text into (frontmatter, body); concatenation restores it."""
    m = FRONTMATTER_REGEX.match(text)
    return (m.group(1), m.group(2)) if m else ("", text)


def partition_fences(text: str) -> tuple[tuple[str, ...], str]:
    """One pass over the lines: (fenced blocks in order, remaining prose).

    CommonMark rules: a closing fence uses the same character, is at least as
    long as the opener, and carries no info string. Unclosed fences are
    treated as prose so malformed markdown cannot hide a validation failure.
    A fence scan is a state machine; a loop is its honest shape.
    """
    blocks: list[str] = []
    prose: list[str] = []
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        m = FENCE_OPEN_REGEX.match(lines[i])
        if not m:
            prose.append(lines[i])
            i += 1
            continue
        fence_char, fence_len = m.group(2)[0], len(m.group(2))
        start = i
        i += 1
        while i < n:
            close = FENCE_OPEN_REGEX.match(lines[i])
            if (
                close
                and close.group(2)[0] == fence_char
                and len(close.group(2)) >= fence_len
                and close.group(3).strip() == ""
            ):
                blocks.append("\n".join(lines[start : i + 1]))
                i += 1
                break
            i += 1
        else:
            prose.extend(lines[start:])
    return tuple(blocks), "\n".join(prose)


def partition_indented(text: str) -> tuple[tuple[str, ...], str]:
    """Indented (4-space/tab) code blocks from fence-free text.

    CommonMark approximation: a run of 4+-indented non-blank lines counts as
    code only when preceded by a blank line (indented code cannot interrupt a
    paragraph) and the nearest preceding non-blank line is not a list item
    (there, 4-space indentation is usually list continuation, not code).
    Blank-separated runs compare as separate blocks; that is symmetric across
    the two texts being validated, which is all equality checking needs.
    """
    blocks: list[str] = []
    prose: list[str] = []
    lines = text.split("\n")
    i, n = 0, len(lines)
    prev_blank = True
    last_nonblank = ""
    while i < n:
        line = lines[i]
        if (
            prev_blank
            and line.strip()
            and INDENTED_LINE_REGEX.match(line)
            and not LIST_ITEM_REGEX.match(last_nonblank)
        ):
            start = i
            while i < n and lines[i].strip() and INDENTED_LINE_REGEX.match(lines[i]):
                i += 1
            blocks.append("\n".join(lines[start:i]))
            prev_blank, last_nonblank = False, lines[i - 1]
            continue
        prose.append(line)
        prev_blank = not line.strip()
        if line.strip():
            last_nonblank = line
        i += 1
    return tuple(blocks), "\n".join(prose)


def markdown_prose(text: str) -> str:
    """Text with fenced and indented code blocks removed."""
    _, rest = partition_fences(text)
    return partition_indented(rest)[1]


def extract_headings(text: str) -> tuple[tuple[str, str], ...]:
    """ATX and setext headings in document order, from fence-free text only,
    so '#' comments inside fenced code are never mistaken for headings.
    Setext levels are recorded as '=' (h1) and '-' (h2)."""
    _, prose = partition_fences(text)
    headings: list[tuple[str, str]] = []
    prev: str | None = None  # candidate paragraph line above a setext underline
    for line in prose.split("\n"):
        if m := ATX_HEADING_REGEX.match(line):
            headings.append((m.group(1), (m.group(2) or "").strip()))
            prev = None
            continue
        if prev is not None and SETEXT_UNDERLINE_REGEX.match(line):
            headings.append(("=" if "=" in line else "-", prev.strip()))
            prev = None
            continue
        prev = line if line.strip() else None
    return tuple(headings)


def _trim_trailing_punctuation(match: str) -> str:
    """Sentence punctuation after a URL or path is prose, not address."""
    return match.rstrip(".,;:!?")


def extract_urls(text: str) -> frozenset[str]:
    return frozenset(map(_trim_trailing_punctuation, URL_REGEX.findall(text)))


def extract_paths(text: str) -> frozenset[str]:
    return frozenset(map(_trim_trailing_punctuation, PATH_REGEX.findall(text)))


def extract_inline_codes(text: str) -> Counter[str]:
    return Counter(re.findall(r"`([^`]+)`", markdown_prose(text)))
