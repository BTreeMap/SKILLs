"""The closed domain: what a file may be, and what an admission may say."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

MAX_FILE_SIZE = 500_000  # bytes; split larger prose files first


class FileKind(Enum):
    NATURAL_LANGUAGE = "natural_language"
    CODE = "code"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Refusal:
    """Invariant violation: the only thing the symbolic side may block on."""

    reason: str


@dataclass(frozen=True, slots=True)
class Assessment:
    """Heuristic reading of a file: a best-guess kind plus the evidence that
    produced it. Advisory by construction: the compressing agent owns the
    judgment; only `Refusal` (exact invariants) blocks."""

    kind: FileKind
    signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Plan:
    """An admitted compression: the single trusted entry into the domain.

    `split_frontmatter` partitions the source text, so the invariant
    `original == frontmatter + body` holds by construction; nothing ever
    needs to re-read the source to recover the original. `notes` carries
    the advisory signals for the agent; it never gates.
    """

    path: Path
    frontmatter: str
    body: str
    notes: tuple[str, ...] = ()

    @property
    def original(self) -> str:
        return self.frontmatter + self.body


Admission = Plan | Refusal


@dataclass(frozen=True, slots=True)
class Verdict:
    """Validation outcome: independent checks concatenate their findings."""

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors
