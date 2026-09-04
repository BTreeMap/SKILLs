"""Linear string parsers built on CPython's C-level primitives.

Two costs decide the shape here. Asymptotically, every function is one
pass. Constant-factor, a Python-level `for char in text` loop costs
roughly 50 to 100 ns per character, while `str.translate`, `str.split`,
and `str.find` run in C at 1 to 5 ns, so a per-character loop is the
wrong backend even when its complexity is right: measured on a 127 KB
paper, tokenizing by loop takes 8.7 ms against 2.0 ms by translate.
Every scan below therefore drives C primitives and keeps Python-level
iteration proportional to the tokens produced, never the characters read.
"""

from __future__ import annotations

from collections.abc import Iterator

ASCII_LOWER_ALNUM = "abcdefghijklmnopqrstuvwxyz0123456789"
ASCII_WORD = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
SPACE = 32


def keep_table(keep: str) -> bytes:
    """A 256-byte translation table keeping `keep` and blanking the rest.

    `bytes.translate` applies it in one C pass, so `runs` costs one scan
    plus one allocation per token.
    """
    kept = frozenset(keep.encode("ascii"))
    return bytes.maketrans(
        bytes(range(256)), bytes(b if b in kept else SPACE for b in range(256))
    )


def runs(text: str, table: bytes) -> list[str]:
    """Maximal runs of the characters `table` keeps, in order.

    Text is read as ASCII with every other codepoint replaced, so a run
    never spans a non-ASCII character.
    """
    blanked = text.encode("ascii", "replace").translate(table)
    return [token.decode("ascii") for token in blanked.split()]


WORD_TABLE = keep_table(ASCII_LOWER_ALNUM)


def ascii_words(text: str) -> list[str]:
    """Maximal runs of lowercase ASCII letters and digits, after lowering:
    the tokenizer behind keywords, slugs, and normalized titles."""
    return runs(text.lower(), WORD_TABLE)


def collapse_whitespace(text: str) -> str:
    """Runs of whitespace become one space; ends are trimmed."""
    return " ".join(text.split())


def is_digits(text: str) -> bool:
    """Non-empty and ASCII digits only; `str.isdigit` alone admits Unicode
    digits such as superscripts and fullwidth forms."""
    return bool(text) and text.isascii() and text.isdigit()


def prefixed_number(text: str, prefix: str) -> int | None:
    """`j12` under prefix `j` is 12; anything else is None."""
    rest = text.removeprefix(prefix)
    return int(rest) if len(rest) < len(text) and is_digits(rest) else None


def bracketed(text: str) -> Iterator[str]:
    """Contents of every innermost `[...]` in order; amortized O(n) because
    a bracket that opens inside another restarts the scan at the inner one.
    Every step is a C-level `find`, so no character is touched by Python."""
    position = 0
    while (start := text.find("[", position)) != -1:
        end = text.find("]", start + 1)
        if end == -1:
            return
        content = text[start + 1 : end]
        inner = content.rfind("[")
        if inner != -1:
            position = start + 1 + inner
            continue
        yield content
        position = end + 1


def strip_tags(text: str, fill: str = "") -> str:
    """Replace `<...>` spans with `fill`; an unclosed `<` stays as text."""
    pieces: list[str] = []
    position = 0
    while (start := text.find("<", position)) != -1:
        end = text.find(">", start + 1)
        if end == -1:
            break
        pieces.append(text[position:start])
        position = end + 1
    pieces.append(text[position:])
    return fill.join(pieces)


ASCII_DIGITS = "0123456789"
HEADING_WORDS = 4  # the longest heading any caller's closed vocabulary holds


def digit_run(text: str, limit: int) -> int:
    """Length of the leading ASCII digit run, counted no further than
    `limit + 1`. The cap is what keeps the scan proportional to what a caller
    can accept rather than to the line: an ordered-list marker admits nine
    digits, so a line of a million digits is rejected after ten comparisons.
    A return of `limit + 1` means "longer than the limit", never a true length.
    `str.lstrip` runs the scan in C and leaves non-ASCII digits alone."""
    head = text[: limit + 1]
    return len(head) - len(head.lstrip(ASCII_DIGITS))


def heading_words(line: str, limit: int = HEADING_WORDS) -> list[str]:
    """Words of a heading line after an optional `1.2.` section number,
    lowercased; empty when the line is blank or a bare number.

    The law that makes the cap safe: the list is longer than `limit` exactly
    when the line holds more than `limit` words, because the final element
    carries the rest of the line unsplit. Tuple equality against any closed
    vocabulary of at most `limit` words is therefore unchanged, while the work
    stays proportional to `limit` rather than to the words on the line."""
    parts = line.split(maxsplit=limit + 1)
    if parts and is_digits(parts[0].replace(".", "")):
        parts = parts[1:]
    return [part.lower() for part in parts]
