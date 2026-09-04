"""The identifier algebra: slugging, minting, resolution, elimination.

Pure except `suffix`/`mint` (randomness).
"""

from __future__ import annotations

import base64
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from btm_corekit.errors import CommandError
from btm_corekit.text import ascii_words

KEYWORD_RANGE = (2, 3)  # advisory band for minting keywords


def keywords_of(text: str) -> list[str]:
    return ascii_words(text)


def slugify(words: Iterable[str]) -> str:
    cleaned = [part for word in words for part in keywords_of(str(word))]
    if not cleaned:
        raise CommandError("identifier keywords must contain letters or digits")
    return "-".join(cleaned)


def band_signal(stem: str) -> str | None:
    """Advisory for a stem outside the keyword band; None inside it."""
    low, high = KEYWORD_RANGE
    if low <= stem.count("-") + 1 <= high:
        return None
    return f"'{stem}': two or three keywords resolve best"


@dataclass(frozen=True, slots=True)
class Exact:
    id: str


@dataclass(frozen=True, slots=True)
class Recovered:
    id: str


@dataclass(frozen=True, slots=True)
class Ambiguous:
    candidates: tuple[str, ...]  # sorted


@dataclass(frozen=True, slots=True)
class NoMatch:
    pass


Resolution = Exact | Recovered | Ambiguous | NoMatch


def resolve(
    ref: str, ids: Iterable[str], keywords: Mapping[str, set[str]] | None = None
) -> Resolution:
    """Total resolution: exact id, else the id whose keywords are a superset.

    Both sides are parsed into keyword sets. A substring test over the raw
    identifier instead lets a keyword match inside a longer word, and inside
    the 26 random base32hex characters of the suffix, where a single letter
    lands better than half the time.

    `keywords` is the caller's own id-to-keyword index, shared with `suggest`;
    without it each call re-tokenizes the pool at O(ids x characters).
    """
    pool = list(ids)
    if ref in pool:
        return Exact(ref)
    wanted = frozenset(keywords_of(ref))
    if not wanted:
        return NoMatch()
    index = keywords or {}
    matches = [
        candidate
        for candidate in pool
        if wanted <= (index.get(candidate) or frozenset(keywords_of(candidate)))
    ]
    if not matches:
        return NoMatch()
    if len(matches) > 1:
        return Ambiguous(tuple(sorted(matches)))
    return Recovered(matches[0])


def eliminate(
    resolution: Resolution, ref: str, kind: str, hint: str | None = None
) -> tuple[str, str | None]:
    """Eliminate a Resolution into (identifier, recovery signal or None).

    Raises CommandError on Ambiguous and NoMatch; `hint` extends the
    NoMatch message with the command that creates the missing subject.
    """
    match resolution:
        case Exact(full):
            return full, None
        case Recovered(full):
            return full, f"recovered {kind} '{ref}' -> {full}; use the full identifier"
        case Ambiguous(candidates):
            raise CommandError(
                f"'{ref}' is ambiguous across {kind}s: {', '.join(candidates)}"
            )
        case NoMatch() if not keywords_of(ref):
            raise CommandError(f"empty {kind} reference")
        case NoMatch():
            tail = f"; {hint}" if hint else ""
            raise CommandError(f"no {kind} matches '{ref}'{tail}")


def suffix() -> str:
    """128 bits of entropy, base32hex, lowercase: uniqueness is the script's job."""
    return base64.b32hexencode(os.urandom(16)).decode().rstrip("=").lower()


def mint(words: Iterable[str]) -> str:
    return f"{slugify(words)}-{suffix()}"


def is_pathlike(argument: str) -> bool:
    return (
        os.sep in argument
        or (os.altsep is not None and os.altsep in argument)
        or argument.startswith(("~", "."))
    )
