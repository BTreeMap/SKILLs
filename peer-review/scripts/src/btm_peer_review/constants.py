"""Closed vocabularies and thresholds the domain is built from."""

from __future__ import annotations

import re
from enum import StrEnum


class Level(StrEnum):
    LITE = "lite"
    FULL = "full"
    ULTRA = "ultra"


class Severity(StrEnum):
    FATAL = "fatal"
    MAJOR = "major"
    MINOR = "minor"
    QUESTION = "question"


class Bank(StrEnum):
    CLAIMS = "claims"
    DESIGN = "design"
    ANALYSIS = "analysis"
    LIMITATIONS = "limitations"
    NOVELTY = "novelty"


class Kind(StrEnum):
    """One way a paper fails; `bank` names the reference file that owns it."""

    UNSUPPORTED = "unsupported"
    OVERREACH = "overreach"
    SPECULATION = "speculation"
    RHETORIC = "rhetoric"
    CONTROL = "control"
    ASSIGNMENT = "assignment"
    DEVIATION = "deviation"
    ATTRITION = "attrition"
    MEASUREMENT = "measurement"
    SELECTIVE = "selective"
    BASELINE = "baseline"
    ABLATION = "ablation"
    DATA = "data"
    REPORTING = "reporting"
    VARIANCE = "variance"
    COMPARISON = "comparison"
    UNITS = "units"
    POWER = "power"
    CIRCULAR = "circular"
    MULTIPLICITY = "multiplicity"
    NULL = "null"
    CAUSAL = "causal"
    METRIC = "metric"
    UNSTATED = "unstated"
    SHALLOW = "shallow"
    MISDESCRIBED = "misdescribed"
    SCOPE = "scope"
    PRIOR = "prior"
    FIRST = "first"
    SOTA = "sota"
    POSITIONING = "positioning"

    @property
    def bank(self) -> Bank:
        return KIND_BANK[self]


BANKS: dict[Bank, tuple[Kind, ...]] = {
    Bank.CLAIMS: (Kind.UNSUPPORTED, Kind.OVERREACH, Kind.SPECULATION, Kind.RHETORIC),
    Bank.DESIGN: (
        Kind.CONTROL,
        Kind.ASSIGNMENT,
        Kind.DEVIATION,
        Kind.ATTRITION,
        Kind.MEASUREMENT,
        Kind.SELECTIVE,
        Kind.BASELINE,
        Kind.ABLATION,
        Kind.DATA,
        Kind.REPORTING,
    ),
    Bank.ANALYSIS: (
        Kind.VARIANCE,
        Kind.COMPARISON,
        Kind.UNITS,
        Kind.POWER,
        Kind.CIRCULAR,
        Kind.MULTIPLICITY,
        Kind.NULL,
        Kind.CAUSAL,
        Kind.METRIC,
    ),
    Bank.LIMITATIONS: (Kind.UNSTATED, Kind.SHALLOW, Kind.MISDESCRIBED, Kind.SCOPE),
    Bank.NOVELTY: (Kind.PRIOR, Kind.FIRST, Kind.SOTA, Kind.POSITIONING),
}
KIND_BANK: dict[Kind, Bank] = {
    kind: bank for bank, kinds in BANKS.items() for kind in kinds
}
LEVEL_BANKS: dict[Level, tuple[Bank, ...]] = {
    Level.LITE: (Bank.CLAIMS, Bank.LIMITATIONS),
    Level.FULL: tuple(Bank),
    Level.ULTRA: tuple(Bank),
}


class Standing(StrEnum):
    GROUNDED = "grounded"
    UNANCHORED = "unanchored"
    UNDATED = "undated"
    WITHDRAWN = "withdrawn"


class ClaimVerdict(StrEnum):
    CONTESTED = "contested"
    QUESTIONED = "questioned"
    STANDING = "standing"


class Recommendation(StrEnum):
    REJECT = "reject"
    MAJOR_REVISION = "major revision"
    MINOR_REVISION = "minor revision"
    NONE = "no objection stands"


class Band(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Anchor resolution: a quote resolves exactly, or by word n-gram coverage.
ANCHOR_GRAM = 4
ANCHOR_COVERAGE = 0.6  # fraction of the quote's n-grams found in the paper
CLAIM_WORDS_MAX = 60  # a contribution claim is a sentence, not a paragraph
ECHO_WARN = 0.5  # share of anchored objections sitting in the paper's Limitations

PAGE_MARKER = re.compile(r"^## PDF page (\d+)\s*$", re.MULTILINE)
WHITESPACE = re.compile(r"\s+")
NON_WORD = re.compile(r"[^a-z0-9]+")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
HEADING_NUMBER = r"(?:\d+(?:\.\d+)*\.?\s+)?"
LIMITATIONS_HEADING = re.compile(
    rf"^\s*{HEADING_NUMBER}limitations?(?:\s+and\s+future\s+work)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
SECTION_END = re.compile(
    rf"^\s*{HEADING_NUMBER}(?:references|bibliography|acknowledg\w*|appendix|"
    r"ethics statement|broader impacts?|conclusions?)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
