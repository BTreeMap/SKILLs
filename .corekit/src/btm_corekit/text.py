"""Linear string parsers built on CPython's C-level primitives.
Every function is one pass; a Python `for char in text` loop costs 50-100 ns
per character against 1-5 ns for `str.translate`/`split`/`find` in C: on a
127 KB paper, tokenizing by loop took 8.7 ms against 2.0 ms by translate."""

from __future__ import annotations

from collections.abc import Iterator

ASCII_LOWER_ALNUM = "abcdefghijklmnopqrstuvwxyz0123456789"
ASCII_WORD = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
SPACE = 32


def keep_table(keep: str) -> bytes:
    """A 256-byte translation table keeping `keep` and blanking the rest, so
    `bytes.translate` applies it in one C pass: one scan per token."""
    kept = frozenset(keep.encode("ascii"))
    return bytes.maketrans(
        bytes(range(256)), bytes(b if b in kept else SPACE for b in range(256))
    )


def runs(text: str, table: bytes) -> list[str]:
    """Maximal runs of the characters `table` keeps, in order; non-ASCII
    codepoints are replaced first, so a run never spans one."""
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
    a bracket that opens inside another restarts the scan at the inner one."""
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
    """Length of the leading ASCII digit run, capped so the scan never goes
    past `limit + 1` characters. A return of `limit + 1` means "longer than
    the limit", never a true length; `str.lstrip` runs the scan in C."""
    head = text[: limit + 1]
    return len(head) - len(head.lstrip(ASCII_DIGITS))


def heading_words(line: str, limit: int = HEADING_WORDS) -> list[str]:
    """Words of a heading line after an optional `1.2.` section number,
    lowercased; empty when the line is blank or a bare number. The list is
    longer than `limit` only when the line truly holds more words, so tuple
    equality against a closed vocabulary of at most `limit` words stays exact
    while the work stays proportional to `limit`, not to the line."""
    parts = line.split(maxsplit=limit + 1)
    if parts and is_digits(parts[0].replace(".", "")):
        parts = parts[1:]
    return [part.lower() for part in parts]
