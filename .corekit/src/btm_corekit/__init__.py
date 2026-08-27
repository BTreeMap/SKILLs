"""btm-corekit: the shared symbolic kernel for SKILLs bundled scripts.

Single definition of the identifier algebra (minting, keyword resolution,
recovery) and session addressing. Consumer scripts declare this package as
an editable uv path dependency on the repository's `.corekit` directory,
so a skill runs from a full repository checkout (marketplace install or
clone) and a script copied out alone fails loudly at environment build.

Purity split: everything here is pure except `suffix`/`mint` (randomness)
and `state_root`/`tree_bytes` (environment and filesystem reads). Signals
are returned as values; consumers render them.
"""

from __future__ import annotations

import base64
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

KEYWORD_RANGE = (2, 3)  # advisory band for minting keywords
NON_SLUG = re.compile(r"[^a-z0-9]+")


class CommandError(Exception):
    """Failure that ends a command with a clean message and exit code 1."""


# --- identifiers: pure ---


def keywords_of(text: str) -> list[str]:
    return [part for part in NON_SLUG.sub("-", text.lower()).split("-") if part]


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


def resolve(ref: str, ids: Iterable[str]) -> Resolution:
    """Total resolution: exact id, else the id containing every keyword.

    O(ids x keywords); pools stay in the low hundreds.
    """
    pool = list(ids)
    if ref in pool:
        return Exact(ref)
    keywords = keywords_of(ref)
    matches = [
        candidate
        for candidate in pool
        if keywords and all(keyword in candidate for keyword in keywords)
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
        case NoMatch():
            tail = f"; {hint}" if hint else ""
            raise CommandError(f"no {kind} matches '{ref}'{tail}")
    raise AssertionError("unreachable: Resolution is a closed union")


# --- effects: randomness, environment, filesystem ---


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


def state_root(skill: str) -> Path:
    """Durable-state home for one skill, per repository convention."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    else:
        base = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    return Path(base) / "btm-skills" / skill


def tree_bytes(path: Path) -> int:
    """Total size of the regular files under a directory."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
