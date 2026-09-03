"""Closed vocabularies and thresholds the domain is built from."""

from __future__ import annotations

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


# Anchor resolution: a quote resolves exactly, or by best-substring similarity.
# Alignment costs O(len(quote) x len(paper) / 64) inside rapidfuzz, so the
# quote is capped: an anchor is a sentence, never a section.
ANCHOR_SIMILARITY = 0.85  # normalized indel similarity that admits an anchor
ANCHOR_HINT_FLOOR = 0.5  # below this the rejection names no page at all
ANCHOR_CHARS_MAX = 1000
# Below this a similarity score is noise: any short string resembles some
# span of a long paper, so a shorter quote resolves verbatim or not at all.
ANCHOR_CHARS_MIN = 12
CLAIM_WORDS_MAX = 60  # a contribution claim is a sentence, not a paragraph
ECHO_WARN = 0.5  # share of anchored objections sitting in the paper's Limitations

PAGE_MARKER = "## PDF page "  # read-pdf's marker line, followed by the number
LIMITATIONS_HEADINGS = frozenset(
    {("limitation",), ("limitations",), ("limitations", "and", "future", "work")}
)
SECTION_END_FIRST_WORDS = frozenset(
    {"references", "bibliography", "appendix", "conclusion", "conclusions"}
)
SECTION_END_PAIRS = frozenset(
    {("ethics", "statement"), ("broader", "impact"), ("broader", "impacts")}
)
