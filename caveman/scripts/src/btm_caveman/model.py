"""The closed domain: what a file may be, and what an admission may say."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from btm_corekit import Diagnostic

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
    """Heuristic reading of a file: a best-guess kind plus its evidence.

    Advisory only; only `Refusal` blocks.
    """

    kind: FileKind
    signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Plan:
    """An admitted compression: the single trusted entry into the domain.

    `original == frontmatter + body` holds by construction. `notes` carries
    advisory signals; it never gates.
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
    """Validation outcome: independent checks concatenate their findings.

    An error carries the check that raised it, so a rejection locates every
    fix; a warning is advisory and travels as text.
    """

    errors: tuple[Diagnostic, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors
