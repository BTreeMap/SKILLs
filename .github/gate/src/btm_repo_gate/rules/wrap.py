"""Markdown prose wrapped to one width; everything that is not prose is kept
byte for byte.

A document is read once, linearly. A scanner state (`Text`, `Fence`, `Raw`,
`Markup`) decides which lines are verbatim by context; the remaining lines
are prose, grouped into `Paragraph` and list `Item` blocks, or verbatim by
their own shape (headings, tables, quotes, indented code, reference
definitions, hard breaks). Rendering wraps the prose blocks and copies the
rest. Three laws hold and the tests check them: the whitespace-normalized
text is unchanged, every verbatim line is unchanged in order, and rendering
is idempotent.
"""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from btm_repo_gate.conventions import WRAP_WIDTH
from btm_repo_gate.repairs import Finding, WriteText
from btm_repo_gate.snapshot import Repo


@dataclass(frozen=True, slots=True)
class Verbatim:
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Paragraph:
    indent: str
    words: str  # whitespace-normalized


@dataclass(frozen=True, slots=True)
class Item:
    lead: str  # indent plus marker plus one space, e.g. "  - " or "1. "
    words: str


Block = Verbatim | Paragraph | Item


@dataclass(frozen=True, slots=True)
class Text:
    """Outside any fence or markup: a line is judged by its own shape."""


@dataclass(frozen=True, slots=True)
class Fence:
    marker: str  # "```" or "~~~"


@dataclass(frozen=True, slots=True)
class Markup:
    """Inside the element a line opened. Only tags of that one name move the
    depth, so a placeholder such as `<skill-root>` or a tag quoted in a code
    span cannot hold the block open past its closing tag."""

    name: str
    depth: int  # open `name` elements; the block ends when it returns to zero


@dataclass(frozen=True, slots=True)
class Raw:
    """Inside CDATA or a comment, where even tags are text."""

    closer: str
    resume: Text | Markup  # the state to restore when the span closes


Scan = Text | Fence | Raw | Markup

# One class, one quantifier per piece: linear on any input.
_ITEM = re.compile(r"^( *)([-*+]|\d+[.)]) +(\S.*)$")
_TAG = re.compile(r"<(/?)([A-Za-z][\w-]*)[^<>]*?(/?)>")
_REFERENCE = re.compile(r"^ *\[[^\]]*\]: ")
_CODE_SPAN = re.compile(r"`[^`]*`")
_VOID_TAGS = frozenset({"br", "hr", "img", "input", "link", "meta"})
_RAW_SPANS = (("<![CDATA[", "]]>"), ("<!--", "-->"))
_FENCES = ("```", "~~~")
_PROSE_STOPS = ("#", "|", "<", ">", *_FENCES)
_CODE_INDENT = 4
_BREAK_MARKS = 3
_NBSP = "\u00a0"


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _is_prose(line: str) -> bool:
    """A line that may be joined and rewrapped, judged by its own shape."""
    stripped = line.lstrip()
    if not stripped or stripped.startswith(_PROSE_STOPS):
        return False
    if line.endswith(("  ", "\\")):
        return False  # a hard line break the author placed
    return not (_is_thematic_break(stripped) or _REFERENCE.match(line))


def _is_thematic_break(stripped: str) -> bool:
    """Three or more of one of `-*_`, spaces allowed between them."""
    marks = stripped.replace(" ", "")
    return len(marks) >= _BREAK_MARKS and len(set(marks)) == 1 and marks[0] in "-*_"


def _markup(line: str, outer: Text | Markup) -> Scan:
    """The state after a markup line: a raw span if one opens and does not
    close on the line, else the element state the line's tags leave."""
    for opener, closer in _RAW_SPANS:
        head, found, tail = line.partition(opener)
        if found and closer not in tail:
            return Raw(closer, _element(head, outer))
    return _element(line, outer)


def _element(line: str, outer: Text | Markup) -> Text | Markup:
    """Outside markup, the line's first tag names the element it opens; a
    closing, self-closing, or void first tag opens none. Inside, only tags
    of the open element's name move its depth."""
    tags = _TAG.findall(line)
    match outer:
        case Markup(name, depth):
            pass
        case Text():
            if not tags:
                return outer
            closing, name, self_closing = tags[0]
            if closing or self_closing or name.lower() in _VOID_TAGS:
                return outer
            depth = 0
    for closing, tag, self_closing in tags:
        if tag == name and not self_closing:
            depth = max(0, depth - 1) if closing else depth + 1
    return Markup(name, depth) if depth else Text()


def _step(state: Scan, line: str) -> tuple[Scan, bool]:
    """The scanner state after `line`, and whether the state alone makes the
    line verbatim."""
    stripped = line.lstrip()
    match state:
        case Raw(closer, resume):
            _, found, tail = line.partition(closer)
            return (_markup(tail, resume) if found else state), True
        case Fence(marker):
            return (Text() if stripped.startswith(marker) else state), True
        case Markup():
            return _markup(line, state), True
        case Text():
            if stripped.startswith(_FENCES):
                return Fence(stripped[:3]), True
            if stripped.startswith("<"):
                return _markup(line, state), True
            return state, False


def _frontmatter_end(lines: Sequence[str]) -> int:
    """Index just past a leading `---` block, or 0 when there is none."""
    if not lines or lines[0] != "---":
        return 0
    end = 1
    while end < len(lines) and lines[end] != "---":
        end += 1
    return min(end + 1, len(lines))


def _continues(line: str, hang: int) -> bool:
    """A prose line indented at least to the hanging column continues an item."""
    return _is_prose(line) and _ITEM.match(line) is None and _indent(line) >= hang


def _prose(lines: Sequence[str], index: int) -> tuple[Item | Paragraph, int]:
    """The prose block starting at `index`, and the index after it."""
    line = lines[index]
    item = _ITEM.match(line)
    count = len(lines)
    if item is not None:
        indent, marker, rest = item.groups()
        lead = f"{indent}{marker} "
        words = [rest]
        index += 1
        while index < count and _continues(lines[index], len(lead)):
            words.append(lines[index])
            index += 1
        return Item(lead, " ".join(" ".join(words).split())), index
    words = [line]
    index += 1
    while index < count and _is_prose(lines[index]) and not _ITEM.match(lines[index]):
        words.append(lines[index])
        index += 1
    return Paragraph(line[: _indent(line)], " ".join(" ".join(words).split())), index


def _blocks(lines: Sequence[str]) -> Iterator[Block]:
    """One pass over `lines`; each line lands in exactly one block."""
    start = _frontmatter_end(lines)
    if start:
        yield Verbatim(tuple(lines[:start]))
    state: Scan = Text()
    index = start
    while index < len(lines):
        line = lines[index]
        state, verbatim = _step(state, line)
        code = _indent(line) >= _CODE_INDENT and _ITEM.match(line) is None
        if verbatim or code or not _is_prose(line):
            yield Verbatim((line,))
            index += 1
            continue
        block, index = _prose(lines, index)
        yield block


def _wrap(words: str, first: str, rest: str, width: int) -> list[str]:
    """Wrap with inline code spans kept whole: spaces inside backticks are
    hidden from the wrapper and restored after."""
    guarded = _CODE_SPAN.sub(lambda m: m.group(0).replace(" ", _NBSP), words)
    wrapped = textwrap.wrap(
        guarded,
        width=width,
        initial_indent=first,
        subsequent_indent=rest,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return [line.replace(_NBSP, " ") for line in wrapped]


def _render(block: Block, width: int) -> Iterator[str]:
    match block:
        case Verbatim(lines):
            yield from lines
        case Paragraph(indent, words):
            yield from _wrap(words, indent, indent, width)
        case Item(lead, words):
            yield from _wrap(words, lead, " " * len(lead), width)


def reflow(text: str, width: int = WRAP_WIDTH) -> str:
    """`text` with prose paragraphs and list items wrapped at `width`."""
    blocks = _blocks(text.split("\n"))
    return "\n".join(line for block in blocks for line in _render(block, width))


def rule_wrap(repo: Repo) -> Iterator[Finding]:
    """Markdown prose sits at one width across the library; wrapping is
    mechanical, so the finding carries the reflowed file."""
    for path, text in repo.texts.items():
        if path.suffix != ".md":
            continue
        wrapped = reflow(text)
        if wrapped != text:
            yield Finding(
                "wrap",
                str(path),
                f"prose reflowed to {WRAP_WIDTH} columns",
                WriteText(path, wrapped),
            )
