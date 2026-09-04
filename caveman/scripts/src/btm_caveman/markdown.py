"""Markdown structure: the regions a compression must leave untouched."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from functools import lru_cache

from btm_corekit import digit_run, keep_table, runs

FENCE_CHARS = frozenset("`~")
BULLET_CHARS = frozenset("-*+")
SEPARATORS = frozenset("/\\")
MAX_INDENT = 3  # CommonMark: four spaces starts indented code
MAX_HEADING = 6
MIN_FENCE = 3
MAX_ORDERED_DIGITS = 9


def _fence_open(line: str) -> tuple[str, int, str] | None:
    """(fence char, fence length, info string) when the line opens a fence:
    up to three whitespace characters, then three or more of one fence char."""
    indent = 0
    while indent < MAX_INDENT and indent < len(line) and line[indent].isspace():
        indent += 1
    rest = line[indent:]
    if rest[:1] not in FENCE_CHARS:
        return None
    char = rest[0]
    length = len(rest) - len(rest.lstrip(char))
    return (char, length, rest[length:]) if length >= MIN_FENCE else None


def _indent_up_to_three(line: str) -> str | None:
    """The line past up to three leading spaces, else None when indented more."""
    indent = len(line) - len(line.lstrip(" "))
    return None if indent > MAX_INDENT else line[indent:]


def atx_heading(line: str) -> tuple[str, str] | None:
    """(hashes, text) for an ATX heading: 1-6 `#`, then space, tab, or end."""
    rest = _indent_up_to_three(line)
    if rest is None or not rest.startswith("#"):
        return None
    hashes = len(rest) - len(rest.lstrip("#"))
    if hashes > MAX_HEADING:
        return None
    after = rest[hashes:]
    if after and after[0] not in " \t":
        return None
    return rest[:hashes], after.strip(" \t")


def setext_underline(line: str) -> str | None:
    """`=` or `-` when the line is a run of that character, else None."""
    rest = _indent_up_to_three(line)
    if rest is None:
        return None
    body = rest.rstrip(" \t")
    if body and (set(body) == {"="} or set(body) == {"-"}):
        return body[0]
    return None


def is_indented_line(line: str) -> bool:
    return line.startswith(("    ", "\t"))


def is_list_item(line: str) -> bool:
    """`-`, `*`, `+`, or `1.`/`1)` (up to nine digits), then a space or tab."""
    rest = _indent_up_to_three(line)
    if rest is None:
        return False
    if rest[:1] in BULLET_CHARS:
        return rest[1:2] in (" ", "\t")
    digits = digit_run(rest, MAX_ORDERED_DIGITS)
    return (
        1 <= digits <= MAX_ORDERED_DIGITS
        and rest[digits : digits + 1] in (".", ")")
        and rest[digits + 1 : digits + 2] in (" ", "\t")
    )


def count_bullets(text: str) -> int:
    """Lines whose first non-blank character is a bullet followed by blank or end."""
    count = 0
    for line in text.split("\n"):
        rest = line.lstrip(" \t")
        if rest[:1] in BULLET_CHARS and (len(rest) == 1 or rest[1] in " \t"):
            count += 1
    return count


def split_frontmatter(text: str) -> tuple[str, str]:
    """Partition text into (frontmatter, body); concatenation restores it.
    Frontmatter opens with `---` on the first line and closes at the next
    line that is exactly `---`; either end may carry `\r`."""
    first_end = text.find("\n")
    if first_end == -1 or text[:first_end].rstrip("\r") != "---":
        return "", text
    position = first_end + 1
    while (line_end := text.find("\n", position)) != -1:
        if text[position:line_end].rstrip("\r") == "---":
            return text[: line_end + 1], text[line_end + 1 :]
        position = line_end + 1
    return "", text


@lru_cache(maxsize=8)
def partition_fences(text: str) -> tuple[tuple[str, ...], str]:
    """One pass over the lines: (fenced blocks in order, remaining prose).

    Closing needs the same character, at least the opener's length, and no
    info string (CommonMark). An unclosed fence counts as prose, so malformed
    markdown cannot hide a validation failure.
    """
    blocks: list[str] = []
    prose: list[str] = []
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        opened = _fence_open(lines[i])
        if opened is None:
            prose.append(lines[i])
            i += 1
            continue
        fence_char, fence_len, _ = opened
        start = i
        i += 1
        while i < n:
            close = _fence_open(lines[i])
            if (
                close is not None
                and close[0] == fence_char
                and close[1] >= fence_len
                and close[2].strip() == ""
            ):
                blocks.append("\n".join(lines[start : i + 1]))
                i += 1
                break
            i += 1
        else:
            prose.extend(lines[start:])
    return tuple(blocks), "\n".join(prose)


@lru_cache(maxsize=8)
def partition_indented(text: str) -> tuple[tuple[str, ...], str]:
    """Indented (4-space/tab) code blocks from fence-free text.

    CommonMark approximation: a run counts as code only when preceded by a
    blank line and not continuing a list item. Blank-separated runs stay
    distinct blocks, which is all the validator's equality check needs.
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
            and is_indented_line(line)
            and not is_list_item(last_nonblank)
        ):
            start = i
            while i < n and lines[i].strip() and is_indented_line(lines[i]):
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
        if (heading := atx_heading(line)) is not None:
            headings.append(heading)
            prev = None
            continue
        if prev is not None and (level := setext_underline(line)) is not None:
            headings.append((level, prev.strip()))
            prev = None
            continue
        prev = line if line.strip() else None
    return tuple(headings)


def _trim_trailing_punctuation(match: str) -> str:
    """Sentence punctuation after a URL or path is prose, not address."""
    return match.rstrip(".,;:!?")


URL = re.compile(r"https?://[^\s)]*")
"""One quantifier over one class: the engine stays linear and runs in C."""


def _urls(text: str) -> Iterator[str]:
    """Every `http(s)://` run up to whitespace or `)`."""
    return (found.group() for found in URL.finditer(text))


PATH_TABLE = keep_table(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./\\:"
)


def _path_runs(text: str) -> list[str]:
    """Maximal runs of path characters, keeping `:` so `C:\\` stays attached."""
    return runs(text, PATH_TABLE)


def _looks_like_path(run: str) -> bool:
    """Given a run that carries a separator: an anchor (`../`, `./`, `/`,
    `X:\\`) with at least one character after it, or a bare word joined to
    more by an interior separator."""
    if run.startswith(("../", "./", "/")):
        return len(run) > run.index("/") + 1
    if run[1:3] == ":\\" and run[:1].isalpha():
        return len(run) > len("X:\\")
    slash, backslash = run.find("/"), run.find("\\")
    if slash == -1:
        separator = backslash
    elif backslash == -1:
        separator = slash
    else:
        separator = min(slash, backslash)
    return 0 < separator < len(run) - 1


def extract_urls(text: str) -> frozenset[str]:
    return frozenset(map(_trim_trailing_punctuation, _urls(text)))


def extract_paths(text: str) -> frozenset[str]:
    return frozenset(
        _trim_trailing_punctuation(run)
        for run in _path_runs(text)
        if _looks_like_path(run)
    )


def _inline_codes(text: str) -> Iterator[str]:
    """Contents of every `` `...` `` span, non-empty."""
    position = 0
    while (start := text.find("`", position)) != -1:
        end = text.find("`", start + 1)
        if end == -1:
            return
        if end > start + 1:
            yield text[start + 1 : end]
            position = end + 1
        else:
            position = end  # an empty pair: its closer may open the next span


def extract_inline_codes(text: str) -> Counter[str]:
    return Counter(_inline_codes(markdown_prose(text)))
