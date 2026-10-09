"""Endpoints, limits, and the closed vocabularies the domain is built from."""

from __future__ import annotations

from enum import StrEnum

from btm_corekit import INDEXES, having

TIMEOUT_SECONDS = 30
RESPONSE_CAP_BYTES = (
    16 * 1024 * 1024
)  # an index page is kilobytes; a cap bounds a stall
DEFAULT_LIMIT = 25
MAX_LIMIT = 100
COURTESY_PAUSE_SECONDS = 0.2
TITLE_MATCH_FLOOR = 0.6
ABSTRACT_SHOW_LIMIT = 1500
AUTHOR_SHOW_LIMIT = 6
PAD_TAIL = 10
HTTP_OK = 200


class Level(StrEnum):
    """How much rigor the review runs at; the bands read off it."""

    BASIC = "basic"
    FULL = "full"
    MAXIMUM = "maximum"


class Status(StrEnum):
    """Where a paper stands in screening. `EXCLUDED` implies a reason; the
    Paper decoder is the one place that holds the implication."""

    CANDIDATE = "candidate"
    INCLUDED = "included"
    EXCLUDED = "excluded"


class ReadLevel(StrEnum):
    """How deeply a paper was read. Ordered by `READ_RANK`, which is the
    order itself rather than an IntEnum, so the value on disk stays a name."""

    NONE = "none"
    ABSTRACT = "abstract"
    FULL_TEXT = "full-text"


class Stage(StrEnum):
    """The screening pass a decision was made in; the report's flow counts
    split exclusions by it."""

    TITLE_ABSTRACT = "title-abstract"
    FULL_TEXT = "full-text"


READ_RANK = {level: rank for rank, level in enumerate(ReadLevel)}
# The argparse and validation surfaces read the vocabulary off the type, so a
# variant can never be added in one place and forgotten in the other.
LEVELS = tuple(Level)
STATUSES = tuple(Status)
READ_LEVELS = tuple(ReadLevel)
STAGES = tuple(Stage)
SOURCES = tuple(INDEXES)
GRAPH_SOURCES = tuple(dict.fromkeys(having("references") + having("citations")))
"""The indexes a snowball can walk, in registry order; openalex leads."""
LOOKUP_SOURCES = having("lookup")
"""The indexes `fill` asks, in registry order."""
DIRECTIONS = ("backward", "forward")
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
